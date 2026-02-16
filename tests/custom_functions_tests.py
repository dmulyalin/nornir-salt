def custom_function_import_test(result):
    ret = []
    if "7.7.7.8" not in result.result:
        ret.append(
            {
                "exception": "Server 7.7.7.8 not in config",
                "result": "FAIL",
                "success": False,
                "description": "check ntp config",
            }
        )
    else:
        ret.append({"exception": "", "result": "PASS", "success": True})
    return ret
