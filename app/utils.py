import base64
import copy
import errno
import jinja2
import json
import logging
import os
import random
import re
import sh
import shutil
import string
import struct
import subprocess
import tempfile
import time
import uuid
import yaml

from OpenSSL import crypto

log = logging.getLogger(__name__)

PASSWORD_CHARS = string.ascii_letters + string.digits


# Disable yaml short-form printing of aliases and anchors
class IgnoreAliasesDumper(yaml.SafeDumper):
    def ignore_aliases(self, *_args, **_kw):
        return True


class ExecUtils(object):
    @staticmethod
    def exec_command(cmd):
        """Executes command and returns tuple of (stdout, errorException)

        Callers should check for errorException == None
        """
        # TODO(modify): modify function to include stderr in output tuple
        cmd = cmd.strip()  # strip whitespace
        try:
            log.debug("executing cmd[{}]".format(cmd))
            res = subprocess.check_output(
                cmd, shell=True, executable='/bin/bash')
            res = res.strip()  # strip whitespace
            log.debug("returned[{}]".format(res))
            return (res, None)
        except subprocess.CalledProcessError as e:
            # Any non-zero exit code will result in a thrown exception
            # The stdout may be accessed with e.output
            # The exit code may be accessed with e.returncode
            return (e.output.rstrip(), e)


class FileUtils(object):
    @staticmethod
    def write_string_to_file(s, file):
        # Allows emit exception in error
        with open(file, "w") as f:
            f.write(s)

    @staticmethod
    def read_string_from_file(file):
        # Allows emit exception in error
        data = ""
        with open(file, "r") as f:
            data = f.read()
        return data

    @staticmethod
    def ensure_removed(fn):
        try:
            os.remove(fn)
        except EnvironmentError as e:
            if e.errno in (errno.EISDIR, errno.EPERM):
                shutil.rmtree(fn)
            elif e.errno != errno.ENOENT:
                raise


class JinjaUtils(object):
    @staticmethod
    def render_jinja(dict_, template_str):
        """Render dict onto jinja template and return the string result"""
        name = 'jvars'
        j2env = jinja2.Environment(
            loader=jinja2.DictLoader({
                name: template_str
            }),
            undefined=jinja2.StrictUndefined,
            extensions=["jinja2.ext.do"])

        # Add some custom jinja filters
        j2env.filters['bool'] = TypeUtils.str_to_bool
        j2env.filters['yaml'] = YamlUtils.yaml_dict_to_string
        j2env.filters['base64encode'] = base64.b64encode

        # Add a "raise" keyword for raising exceptions from within jinja
        j2env.globals['raise'] = JinjaUtils._jinja_keyword_raise
        j2env.globals['gen_names'] = JinjaUtils._jinja_keyword_gen_names
        j2env.globals['mkpass'] = JinjaUtils.mkpass
        j2env.globals['keygen'] = JinjaUtils.keygen
        j2env.globals['self_signed_cert_gen'] = JinjaUtils.self_signed_cert_gen
        j2env.globals['ceph_key'] = JinjaUtils.ceph_key
        j2env.globals['uuid'] = JinjaUtils.uuid

        # Render the template
        rendered_template = j2env.get_template(name).render(dict_)
        return rendered_template + "\n"

    @staticmethod
    def dict_self_render(dict_):
        """Render dict_ values containing nested jinja variables

        Resolve these values by rendering the jinja dict on itself, as many
        times as jinja variables contain other jinja variables.  Stop when the
        rendered output stops changing.
        """
        d = copy.deepcopy(dict_)
        template = None
        for i in range(0, 10):
            template = YamlUtils.yaml_dict_to_string_jinja(d)
            rendered_template = JinjaUtils.render_jinja(d, template)
            d = YamlUtils.yaml_dict_from_string(rendered_template)
            if rendered_template.strip() == template.strip():
                return d
        raise Exception("Unable to fully render jinja variables")

    @staticmethod
    def _jinja_keyword_raise(message):
        # Function to help create a "raise" error keyword in jinja
        raise Exception(message)

    @staticmethod
    def _jinja_keyword_gen_names(prefix, count):
        """
        Function to help generate a list of resource names given a prefix and
        a count.  For example, if prefix is "mariadb" and count is 2, it
        will return list ['mariadb-0001', 'mariadb-0002'].  If prefix is
        "mariadb" and count is 1 or None, it will return list ['mariadb'].
        """

        # Handle count values None and non-num values by squashing to 1
        try:
            count = int(count)
        except Exception:
            count = 1
        # Calculate and return the resource names
        if not count:
            raise Exception("Count cannot be 0")
        if count == 1:
            return [prefix]
        return ['{}-{:04}'.format(prefix, i) for i in range(1, count + 1)]

    @staticmethod
    def mkpass(length=16):
        return ''.join(random.choice(PASSWORD_CHARS) for _idx in range(length))

    @staticmethod
    def keygen(keytype='rsa', bits=4096, comment='', passphrase=''):
        ''' generates an ssh key, returns a (priv, pub) tuple. '''
        # We have to manage two files here, so just handle the files manually
        tmpdir = tempfile.mkdtemp(prefix='keygen')
        try:
            priv_path = os.path.join(tmpdir, 'key')
            pub_path = priv_path + '.pub'

            sh.ssh_keygen(
                t=keytype,
                b=bits,
                q=True,
                C=comment,
                N=passphrase,
                f=priv_path,
                _in=os.devnull,
                _tty_in=False,
                _tty_out=False)
            with open(priv_path, 'r') as priv, open(pub_path, 'r') as pub:
                return priv.read(), pub.read()

        finally:
            FileUtils.ensure_removed(tmpdir)

    @staticmethod
    def self_signed_cert_gen(
            key_type=crypto.TYPE_RSA,
            key_bits=4096,
            country="US",
            state_province="California",
            locality="San Francisco",
            org="Your Company",
            org_unit="Team",
            common_name="www.domain.com",
            subject_alt_names=[],  # alternative dns names as list
            # ^ must look like: ["DNS:*.domain.com", "DNS:domain.ym"]
            validity_days=10 * 365):

        # Create a key pair
        k = crypto.PKey()
        k.generate_key(key_type, key_bits)

        # Create a self-signed cert
        cert = crypto.X509()
        cert.get_subject().C = country
        cert.get_subject().ST = state_province
        cert.get_subject().L = locality
        cert.get_subject().O = org
        cert.get_subject().OU = org_unit
        cert.get_subject().CN = common_name
        if subject_alt_names:
            subject_alt_names = ", ".join(subject_alt_names).encode("utf-8")
            cert.add_extensions([
                crypto.X509Extension("subjectAltName".encode("utf-8"), False,
                                     subject_alt_names)
            ])
        cert.set_serial_number(random.getrandbits(64))
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(validity_days * 24 * 60 * 60)
        cert.set_issuer(cert.get_subject())  # self-signer
        cert.set_pubkey(k)
        cert.sign(k, 'sha1')

        # return a tuple of the private key and the self-signed cert
        return (crypto.dump_privatekey(crypto.FILETYPE_PEM, k),
                crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

    @staticmethod
    def ceph_key():
        # Get 16 random bytes
        key = os.urandom(16)

        # Construct a header for the key
        creation = time.time()
        secs = int(creation)
        nanosecs = int((creation - secs) * 1e9)
        header = struct.pack('<hiih', 1, secs, nanosecs, len(key))

        # Encode and return the key
        return base64.b64encode(header + key).decode('ascii')

    @staticmethod
    def uuid():
        # Generate and return a stringified UUID
        return str(uuid.uuid4())


class StringUtils(object):
    @staticmethod
    def pad_str(pad, num, s):
        return re.sub("^", (pad * num), s, 0, re.MULTILINE)


class TypeUtils(object):
    @staticmethod
    def str_to_bool(text):
        if not text:
            return False
        if text.lower() in ['true', 'yes']:
            return True
        return False


class YamlUtils(object):
    @staticmethod
    def yaml_dict_to_string(dict_):
        """Convert dict to string for human output"""
        # Use width=1000000 to prevent wrapping
        return yaml.safe_dump(dict_, default_flow_style=False, width=1000000)

    @staticmethod
    def yaml_dict_to_string_jinja(dict_):
        """Convert dict to string for jinja processing

        Use this only for dict strings that jinja will process.  If
        you use the normal style instead of double-quote style, then
        yaml dump will escape all single quotes (') by doubling them
        up ('').  If jinja is to process the string, it will fail.
        Thus, change the quote style to avoid escaping single quote
        (').
        """
        # Use width=1000000 to prevent wrapping
        # Use double-quote style to prevent escaping of ' to ''
        return yaml.dump(
            dict_,
            Dumper=IgnoreAliasesDumper,
            default_flow_style=False,
            width=1000000,
            default_style='"')

    @staticmethod
    def yaml_dict_from_string(string_):
        # Use BaseLoader to keep "True|False" strings as strings
        return yaml.load(string_, Loader=yaml.loader.BaseLoader)

    @staticmethod
    def yaml_dict_to_file(dict_, file_):
        s = YamlUtils.yaml_dict_to_string(dict_)
        return FileUtils.write_string_to_file(s, file_)

    @staticmethod
    def yaml_dict_from_file(file):
        s = FileUtils.read_string_from_file(file)
        return YamlUtils.yaml_dict_from_string(s)


class JsonUtils(object):
    @staticmethod
    def json_dict_to_string(dict_):
        """Convert dict to string for human output"""
        # Use width=1000000 to prevent wrapping
        return json.dumps(dict_, sort_keys=True)

    @staticmethod
    def json_dict_from_string(string_):
        # Use BaseLoader to keep "True|False" strings as strings
        return json.loads(string_)

    @staticmethod
    def json_dict_to_file(dict_, file_):
        s = JsonUtils.json_dict_to_string(dict_)
        return FileUtils.write_string_to_file(s, file_)

    @staticmethod
    def json_dict_from_file(file):
        s = FileUtils.read_string_from_file(file)
        return JsonUtils.json_dict_from_string(s)


class KubeUtils(object):
    @staticmethod
    def find_api_url(context):
        """Executes kubectl config view

        Returns either None or a string with API server url.

        Callers should check for returned string if it is not == None
        """
        res, code = ExecUtils.exec_command('kubectl config current-context')
        if code is not None:
            return ('', code)

        current_context = res

        res, code = ExecUtils.exec_command('kubectl config view')
        if code is not None:
            return ('', code)

        configuration = YamlUtils.yaml_dict_from_string(res)

        for cluster in configuration['clusters']:
            server = cluster['cluster']['server']
            context = cluster['name']
            if context == current_context:
                return server
