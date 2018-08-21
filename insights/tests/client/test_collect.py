# -*- coding: UTF-8 -*-

from contextlib import contextmanager
from insights.client.client import collect
from insights.client.config import InsightsConfig
from json import dump as json_dump, dumps as json_dumps
from mock.mock import Mock, patch, PropertyMock
from pytest import mark, raises
from tempfile import NamedTemporaryFile, TemporaryFile


stdin_uploader_json = {"some key": "some value"}
stdin_sig = "some signature"
stdin_payload = {"uploader.json": json_dumps(stdin_uploader_json), "sig": stdin_sig}
remove_files = ["/etc/insights-client/remove.conf", "/tmp/remove.conf"]


def collect_args(*insights_config_args, **insights_config_custom_kwargs):
    """
    Instantiates InsightsConfig with a default logging_file argument.
    """
    all_insights_config_kwargs = {"logging_file": "/tmp/insights.log"}
    all_insights_config_kwargs.update(insights_config_custom_kwargs)
    return InsightsConfig(*insights_config_args, **all_insights_config_kwargs), Mock()


@contextmanager
def patch_temp_conf_file():
    """
    Creates a valid temporary config file.
    """
    collection_rules_file = NamedTemporaryFile("w+t")
    json_dump({"version": "1.2.3"}, collection_rules_file)
    collection_rules_file.seek(0)
    with patch("insights.client.collection_rules.constants.collection_rules_file", collection_rules_file.name):
        yield collection_rules_file
    collection_rules_file.close()


def temp_conf_file():
    """
    Creates a valid temporary config file.
    """
    collection_rules_file = NamedTemporaryFile()
    json_dump({"version": "1.2.3"}, collection_rules_file)
    collection_rules_file.seek(0)
    return collection_rules_file


def patch_get_branch_info():
    """
    Sets a static response to get_branch_info method.
    """
    def decorator(old_function):
        patcher = patch("insights.client.client.get_branch_info")
        return patcher(old_function)
    return decorator


def patch_stdin():
    """
    Sets a static JSON data to stdin.
    """
    def decorator(old_function):
        stdin = TemporaryFile("w+t")
        json_dump(stdin_payload, stdin)
        stdin.seek(0)

        patcher = patch("insights.client.client.sys.stdin", new_callable=PropertyMock(return_value=stdin))
        return patcher(old_function)
    return decorator


def patch_get_conf_stdin():
    """
    Mocks InsightsUploadConf.get_conf_stdin.
    """
    def decorator(old_function):
        patcher = patch("insights.client.client.InsightsUploadConf.get_conf_stdin")
        return patcher(old_function)
    return decorator


def patch_get_conf_file():
    """
    Mocks InsightsUploadConf.get_conf_file so it returns a fixed configuration.
    """
    def decorator(old_function):
        patcher = patch("insights.client.client.InsightsUploadConf.get_conf_file")
        return patcher(old_function)
    return decorator


def patch_get_rm_conf():
    """
    Mocks InsightsUploadConf.get_rm_conf so it returns a fixed configuration.
    """
    def decorator(old_function):
        patcher = patch("insights.client.client.InsightsUploadConf.get_rm_conf")
        return patcher(old_function)
    return decorator


def patch_data_collector():
    """
    Replaces DataCollector with a dummy mock.
    """
    def decorator(old_function):
        patcher = patch("insights.client.client.DataCollector")
        return patcher(old_function)
    return decorator


def patch_isfile(remove_file_exists):
    """
    Mocks os.path.isfile so it always claims that a file exists. If it‘s a remove conf file, the result depends on the
    given value.
    """
    def decorator(old_function):
        remove_file = "/tmp/remove.conf"

        def decider(*args, **kwargs):
            if args[0] == remove_file:
                return remove_file_exists
            else:
                return True

        isfile_patcher = patch("insights.client.collection_rules.os.path.isfile", decider)
        isfile_patched = isfile_patcher(old_function)

        collection_remove_file_patcher = patch("insights.client.collection_rules.constants.collection_remove_file",
                                               remove_file)
        return collection_remove_file_patcher(isfile_patched)
    return decorator


def patch_raw_config_parser():
    """
    Mocks RawConfigParser, so it returns a fixed configuration of removed files.
    """
    def decorator(old_function):
        files = ",".join(remove_files)
        patcher = patch("insights.client.collection_rules.ConfigParser.RawConfigParser",
                        **{"return_value.items.return_value": [("files", files)]})
        return patcher(old_function)
    return decorator


def patch_validate_gpg_sig(return_value):
    """
    Mocks the InsightsUploadConf.validate_gpg_sig method so it returns the given validation result.
    """
    def decorator(old_function):
        patcher = patch("insights.client.collection_rules.InsightsUploadConf.validate_gpg_sig",
                        return_value=return_value)
        return patcher(old_function)
    return decorator


def patch_try_disk(return_value):
    """
    Mocks the InsightsUploadConf.try_disk method so it returns the given parsed file contents.
    """
    def decorator(old_function):
        patcher = patch("insights.client.collection_rules.InsightsUploadConf.try_disk", return_value=return_value)
        return patcher(old_function)
    return decorator


@patch_data_collector()
@patch_get_conf_file()
@patch_get_conf_stdin()
@patch_get_branch_info()
def test_get_conf_file(get_branch_info, get_conf_stdin, get_conf_file, data_collector):
    """
    If there is no config passed via stdin, it is loaded from a file instead.
    """
    config, pconn = collect_args()
    collect(config, pconn)

    get_conf_stdin.assert_not_called()
    get_conf_file.assert_called_once_with()


@patch_data_collector()
@patch_get_conf_file()
@patch_get_conf_stdin()
@patch_stdin()
@patch_get_branch_info()
def test_get_conf_stdin(get_branch_info, stdin, get_conf_stdin, get_conf_file, data_collector):
    """
    If there is config passed via stdin, use it and do not look for it in files.
    """
    config, pconn = collect_args(from_stdin=True)
    collect(config, pconn)

    get_conf_stdin.assert_called_once_with(stdin_payload)
    get_conf_file.assert_not_called()


@patch_data_collector()
@patch_get_rm_conf()
@patch_get_conf_stdin()
@patch_stdin()
@patch_get_branch_info()
def test_get_rm_conf_stdin(get_branch_info, stdin, get_conf_stdin, get_rm_conf, data_collector):
    """
    Load configuration of files removed from collection when collection rules are loaded from stdin.
    """
    config, pconn = collect_args(from_stdin=True)
    collect(config, pconn)

    get_rm_conf.assert_called_once_with()


@patch_data_collector()
@patch_get_rm_conf()
@patch_get_conf_file()
@patch_get_branch_info()
def test_get_rm_conf_file(get_branch_info, get_conf_file, get_rm_conf, data_collector):
    """
    Load configuration of files removed from collection when collection rules are loaded from a file.
    """
    config, pconn = collect_args(from_stdin=False)
    collect(config, pconn)

    get_rm_conf.assert_called_once_with()


@patch_data_collector()
@patch_get_rm_conf()
@patch_get_conf_stdin()
@patch_stdin()
@patch_get_branch_info()
def test_data_collector_stdin(get_branch_info, stdin, get_conf_stdin, get_rm_conf, data_collector):
    """
    Configuration from stdin is passed to the DataCollector along with removed files configuration.
    """
    config, pconn = collect_args(from_stdin=True)
    collect(config, pconn)

    collection_rules = get_conf_stdin.return_value
    rm_conf = get_rm_conf.return_value
    branch_info = get_branch_info.return_value
    data_collector.return_value.run_collection.assert_called_once_with(collection_rules, rm_conf, branch_info)
    data_collector.return_value.done.assert_called_once_with(collection_rules, rm_conf)


@patch_data_collector()
@patch_get_rm_conf()
@patch_get_conf_file()
@patch_get_branch_info()
def test_data_collector_file(get_branch_info, get_conf_file, get_rm_conf, data_collector):
    """
    Configuration from a file is passed to the DataCollector along with removed files configuration.
    """
    config, pconn = collect_args(from_stdin=False)
    collect(config, pconn)

    collection_rules = get_conf_file.return_value
    rm_conf = get_rm_conf.return_value
    branch_info = get_branch_info.return_value
    data_collector.return_value.run_collection.assert_called_once_with(collection_rules, rm_conf, branch_info)
    data_collector.return_value.done.assert_called_once_with(collection_rules, rm_conf)


@mark.regression
@patch_data_collector()
@patch_validate_gpg_sig(False)
@patch_isfile(False)
@patch_stdin()
@patch_get_branch_info()
def test_stdin_signature_ignored(get_branch_info, stdin, validate_gpg_sig, data_collector):
    """
    Signature of configuration from stdin is not validated if validation is disabled.
    """
    config, pconn = collect_args(from_stdin=True, gpg=False)
    collect(config, pconn)

    validate_gpg_sig.assert_not_called()


@mark.regression
@patch_data_collector()
@patch_validate_gpg_sig(True)
@patch_isfile(False)
@patch_stdin()
@patch_get_branch_info()
def test_stdin_signature_valid(get_branch_info, stdin, validate_gpg_sig, data_collector):
    """
    Correct signature of configuration from stdin is recognized.
    """
    config, pconn = collect_args(from_stdin=True)
    collect(config, pconn)

    validate_gpg_sig.assert_called_once()


@mark.regression
@patch_data_collector()
@patch_validate_gpg_sig(False)
@patch_isfile(False)
@patch_stdin()
@patch_get_branch_info()
def test_stdin_signature_invalid(get_branch_info, stdin, validate_gpg_sig, data_collector):
    """
    Incorrect signature of configuration from stdin causes failure.
    """
    config, pconn = collect_args(from_stdin=True)
    with raises(Exception):
        collect(config, pconn)

    validate_gpg_sig.assert_called_once()


@mark.regression
@patch_data_collector()
@patch_validate_gpg_sig(True)
@patch_raw_config_parser()
@patch_isfile(True)
@patch_stdin()
@patch_get_branch_info()
def test_stdin_result(get_branch_info, stdin, raw_config_parser, validate_gpg_sig, data_collector):
    """
    Configuration from stdin is loaded from the "uploader.json" key.
    """
    config, pconn = collect_args(from_stdin=True)
    collect(config, pconn)

    collection_rules = stdin_uploader_json
    rm_conf = {"files": remove_files}
    branch_info = get_branch_info.return_value
    data_collector.return_value.run_collection.assert_called_once_with(collection_rules, rm_conf, branch_info)
    data_collector.return_value.done.assert_called_once_with(collection_rules, rm_conf)


@mark.regression
@patch_data_collector()
@patch_validate_gpg_sig(False)
@patch_isfile(False)
@patch_get_branch_info()
def test_file_signature_ignored(get_branch_info, validate_gpg_sig, data_collector):
    """
    Signature of configuration from a file is not validated if validation is disabled.
    """

    config, pconn = collect_args(from_stdin=False, gpg=False)
    with patch_temp_conf_file():
        collect(config, pconn)

    validate_gpg_sig.assert_not_called()


@mark.regression
@patch_data_collector()
@patch_validate_gpg_sig(True)
@patch_isfile(False)
@patch_stdin()
@patch_get_branch_info()
def test_file_signature_valid(get_branch_info, stdin, validate_gpg_sig, data_collector):
    """
    Correct signature of configuration from a file is recognized.
    """
    config, pconn = collect_args(from_stdin=False)
    with patch_temp_conf_file():
        collect(config, pconn)

    validate_gpg_sig.assert_called_once()


@mark.regression
@patch_data_collector()
@patch_validate_gpg_sig(False)
@patch_isfile(False)
@patch_stdin()
@patch_get_branch_info()
def test_file_signature_invalid(get_branch_info, stdin, validate_gpg_sig, data_collector):
    """
    Incorrect signature of configuration from a file skips that file.
    """
    config, pconn = collect_args(from_stdin=False)
    with patch_temp_conf_file():
        with raises(ValueError):
            collect(config, pconn)

    validate_gpg_sig.assert_called()


@mark.regression
@patch_data_collector()
@patch_raw_config_parser()
@patch_isfile(True)
@patch_try_disk({"version": "1.2.3"})
@patch_get_branch_info()
def test_file_result(get_branch_info, try_disk, raw_config_parser, data_collector):
    """
    Configuration from file is loaded from the "uploader.json" key.
    """
    config, pconn = collect_args(from_stdin=False)
    collect(config, pconn)

    name, args, kwargs = try_disk.mock_calls[0]
    collection_rules = try_disk.return_value.copy()
    collection_rules.update({"file": args[0]})

    rm_conf = {"files": remove_files}
    branch_info = get_branch_info.return_value

    data_collector.return_value.run_collection.assert_called_once_with(collection_rules, rm_conf, branch_info)
    data_collector.return_value.done.assert_called_once_with(collection_rules, rm_conf)


@mark.regression
@patch_data_collector()
@patch_try_disk({"value": "abc"})
@patch_get_branch_info()
def test_file_no_version(get_branch_info, try_disk, data_collector):
    """
    Configuration from file is loaded from the "uploader.json" key.
    """
    config, pconn = collect_args(from_stdin=False)
    with raises(ValueError):
        collect(config, pconn)

    data_collector.return_value.run_collection.assert_not_called()
    data_collector.return_value.done.assert_not_called()


@mark.regression
@patch_data_collector()
@patch_try_disk(None)
@patch_get_branch_info()
def test_file_no_data(get_branch_info, try_disk, data_collector):
    """
    Configuration from file is loaded from the "uploader.json" key.
    """
    config, pconn = collect_args(from_stdin=False)
    with raises(ValueError):
        collect(config, pconn)

    data_collector.return_value.run_collection.assert_not_called()
    data_collector.return_value.done.assert_not_called()
