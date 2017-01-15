import base64
import datetime
import mock
import os
import pytest
import sh
import struct
import tempfile
import time
import uuid

from OpenSSL import crypto

from app import utils

test_conf_self_referencing = '''
    "n1":
      "nn1": "n1_nn1_v"
      "nn2": "{{ n3.nn1 }}"
    "n2": "{{ n1.nn1 }}"
    "n3":
      "nn1": "n3_nn1_v"
      "nn2": "n3_nn2_v"
    "n4": "{{ n2 }}"
    "n5":
      "nn1": "n5_nn1_v"
    "n6": "n6_v"
'''

test_conf_self_rendered = '''
    "n1":
      "nn1": "n1_nn1_v"
      "nn2": "n3_nn1_v"
    "n2": "n1_nn1_v"
    "n3":
      "nn1": "n3_nn1_v"
      "nn2": "n3_nn2_v"
    "n4": "n1_nn1_v"
    "n5":
      "nn1": "n5_nn1_v"
    "n6": "n6_v"
'''


class TestHelper():
    """Helper class for the tests in this file"""

    _test_dir = None

    @staticmethod
    def get_test_dir():
        if TestHelper._test_dir is None:
            TestHelper._test_dir = TestHelper._create_test_dir()
        return TestHelper._test_dir

    @staticmethod
    def _create_test_dir():
        dir_prefix = os.path.join(
            "/tmp", 'app-tests_' + datetime.datetime.fromtimestamp(time.time(
            )).strftime('%Y%m%d%H%M%S') + "_")
        tmp_dir_path = tempfile.mkdtemp(prefix=dir_prefix)
        return tmp_dir_path


class TestExecUtils(TestHelper):
    def test_exec_command(self):

        # Will Succeed
        output, exception = utils.ExecUtils.exec_command('ps')
        assert output is not None and len(output) > 0
        assert exception is None
        # Will Fail
        output, exception = utils.ExecUtils.exec_command('not_a_command')
        assert output is not None and len(output) == 0
        assert exception is not None and len(str(exception)) > 0


class TestFileUtils(TestHelper):
    def test_write_and_read_file(self):
        write_content = "Hello_world\n"
        filename = os.path.join(
            TestHelper.get_test_dir(),
            self.__class__.__name__ + "_test_write_and_read_file.txt")
        utils.FileUtils.write_string_to_file(write_content, filename)
        read_content = utils.FileUtils.read_string_from_file(filename)
        assert write_content == read_content


def test_ensure_removed_dir(tmpdir):
    d = tmpdir.mkdir('sub')
    assert d.check(dir=True)
    utils.FileUtils.ensure_removed(d.strpath)
    assert d.check(exists=False)
    utils.FileUtils.ensure_removed(d.strpath)


def test_ensure_removed_file(tmpdir):
    f = tmpdir.join('meow')
    f.write('wat')
    assert f.check(file=True)
    utils.FileUtils.ensure_removed(f.strpath)
    assert f.check(exists=False)
    utils.FileUtils.ensure_removed(f.strpath)


class TestJinjaUtils(TestHelper):
    def test_self_render(self):
        d1 = utils.YamlUtils.yaml_dict_from_string(test_conf_self_referencing)
        d2 = utils.JinjaUtils.dict_self_render(d1)
        d3 = utils.YamlUtils.yaml_dict_from_string(test_conf_self_rendered)
        assert utils.YamlUtils.yaml_dict_to_string(d2) == \
            utils.YamlUtils.yaml_dict_to_string(d3)

    def test_jinja_keyword_raise(self):
        try:
            utils.JinjaUtils._jinja_keyword_raise("message")
            assert False, "Should never get here"
        except Exception as e:
            assert e is not None

    def test_jinja_keyword_gen_names(self):
        l = utils.JinjaUtils._jinja_keyword_gen_names('prefix', 1)
        assert len(l) == 1
        assert 'prefix' in l

        l = utils.JinjaUtils._jinja_keyword_gen_names('prefix', 2)
        assert len(l) == 2
        assert 'prefix-0001' in l
        assert 'prefix-0002' in l

    def test_mkpass(self):
        assert len(utils.JinjaUtils.mkpass(length=99)) == 99

    def test_keygen(self):
        comment = 'Hello how are you I\'m a turtle'
        try:
            priv, pub = utils.JinjaUtils.keygen(
                bits=1024, keytype='rsa', comment=comment)
        except sh.CommandNotFound:
            pytest.skip('ssh-keygen is not available')

        assert 'RSA PRIVATE KEY' in priv
        assert pub.endswith(comment + '\n')

    def test_self_signed_cert_gen(self):
        # Test cert settings
        key_type = crypto.TYPE_RSA
        key_bits = 3072
        country = "US"
        state_province = "Alaska"
        locality = "Anchorage"
        org = "Test Org"
        org_unit = "Test Unit"
        common_name = "test.domain.com"
        subject_alt_names = ["DNS:*.sub.domain.com", "DNS:domain.top"]
        validity_days = 1 * 365

        # Create the cert
        priv_key, cert = utils.JinjaUtils.self_signed_cert_gen(
            key_type=key_type,
            key_bits=key_bits,
            country=country,
            state_province=state_province,
            locality=locality,
            org=org,
            org_unit=org_unit,
            common_name=common_name,
            subject_alt_names=subject_alt_names,  # alternative dns names list
            validity_days=validity_days)

        # Check taht the cert and priv_key have been created
        assert priv_key and len(priv_key) > 0
        assert cert and len(cert) > 0

        # Load the cert and read the details
        c = crypto.load_certificate(crypto.FILETYPE_PEM, cert)
        key = c.get_pubkey()
        subject = c.get_subject()

        # Read back and check the cert
        assert subject.C == country
        assert subject.ST == state_province
        assert subject.L == locality
        assert subject.O == org
        assert subject.OU == org_unit
        assert subject.CN == common_name
        assert key.type() == key_type
        assert key.bits() == key_bits
        c.get_extension(0) == ", ".join(subject_alt_names)

    @mock.patch.object(utils.os, 'urandom', return_value=b'0123456789012345')
    def test_ceph_key(self, mock_urandom):
        result = utils.JinjaUtils.ceph_key()

        # First, decode the base64
        raw_result = base64.b64decode(result.encode('ascii'))

        # Decompose into a header and a key
        hdr_struct = struct.Struct('<hiih')
        header = raw_result[:hdr_struct.size]
        key = raw_result[hdr_struct.size:]

        # Interpret the header
        _type, _secs, _nanosecs, key_len = hdr_struct.unpack(header)
        assert key_len == len(key)

        # Verify that the key is what it should be
        assert key == b'0123456789012345'

    def test_uuid(self):
        # Grab a UUID object
        uuid_value = uuid.uuid4()

        # Get the result of calling the uuid helper
        with mock.patch.object(utils.uuid, 'uuid4', return_value=uuid_value):
            result = utils.JinjaUtils.uuid()

        # Verify that it's what we expected
        assert result == str(uuid_value)


class TestStringUtils(TestHelper):
    def test_pad_str(self):
        assert utils.StringUtils.pad_str(" ", 2, "") == "  "
        assert utils.StringUtils.pad_str(" ", 3, "  ") == "     "
        assert utils.StringUtils.pad_str("  ", 3, " ") == "       "
        assert utils.StringUtils.pad_str("aa", 2, "") == "aaaa"


class TestTypeUtils(TestHelper):

    scenarios = [
        ('none', dict(
            text=None, expect=False)),
        ('empty', dict(
            text='', expect=False)),
        ('junk', dict(
            text='unlikely', expect=False)),
        ('no', dict(
            text='no', expect=False)),
        ('yes', dict(
            text='yes', expect=True)),
        ('0', dict(
            text='0', expect=False)),
        ('1', dict(
            text='1', expect=False)),
        ('True', dict(
            text='True', expect=True)),
        ('False', dict(
            text='False', expect=False)),
        ('true', dict(
            text='true', expect=True)),
        ('false', dict(
            text='false', expect=False)),
        ('shouty', dict(
            text='TRUE', expect=True)),
    ]

    def test_str_to_bool(self):
        for scenario_name, scenario in TestTypeUtils.scenarios:
            input_text = scenario['text']
            expected_result = scenario['expect']
            calculated_result = utils.TypeUtils.str_to_bool(input_text)
            assert expected_result == calculated_result


class TestYamlUtils(TestHelper):
    def test_write_and_read_string(self):
        dict1 = utils.YamlUtils.yaml_dict_from_string(test_conf_self_rendered)
        str1 = utils.YamlUtils.yaml_dict_to_string(dict1)
        dict2 = utils.YamlUtils.yaml_dict_from_string(str1)
        str2 = utils.YamlUtils.yaml_dict_to_string(dict2)
        assert str1 == str2

    def test_write_and_read_file(self):
        filename = os.path.join(
            TestHelper.get_test_dir(),
            self.__class__.__name__ + "_test_write_and_read_file.txt")
        dict1 = utils.YamlUtils.yaml_dict_from_string(test_conf_self_rendered)
        utils.YamlUtils.yaml_dict_to_file(dict1, filename)
        dict2 = utils.YamlUtils.yaml_dict_from_file(filename)
        str1 = utils.YamlUtils.yaml_dict_to_string(dict1)
        str2 = utils.YamlUtils.yaml_dict_to_string(dict2)
        assert str1 == str2
