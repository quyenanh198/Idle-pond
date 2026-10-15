extends GutTest


func test_parse_success():
	var r := SupabaseClient.parse_response(HTTPRequest.RESULT_SUCCESS, 200, '{"a": 1}'.to_utf8_buffer())
	assert_true(r.ok)
	assert_eq(r.data.a, 1.0)


func test_parse_http_error_message():
	var r := SupabaseClient.parse_response(HTTPRequest.RESULT_SUCCESS, 400, '{"msg": "Invalid login"}'.to_utf8_buffer())
	assert_false(r.ok)
	assert_eq(r.error, "Invalid login")
	var r2 := SupabaseClient.parse_response(HTTPRequest.RESULT_SUCCESS, 502, "<html>bad gateway</html>".to_utf8_buffer())
	assert_eq(r2.error, "HTTP 502")


func test_parse_network_error():
	var r := SupabaseClient.parse_response(HTTPRequest.RESULT_CANT_CONNECT, 0, PackedByteArray())
	assert_false(r.ok)
	assert_string_contains(r.error, "network")


func test_session_from_auth():
	var data := {"access_token": "a", "refresh_token": "r", "expires_in": 3600, "user": {"id": "u1"}}
	assert_eq(SupabaseClient.session_from_auth(data, 100.0), {"access_token": "a", "refresh_token": "r", "expires_at": 3700.0, "user_id": "u1"})
	assert_eq(SupabaseClient.session_from_auth({"error": "x"}, 100.0), {})
	assert_eq(SupabaseClient.session_from_auth(null, 100.0), {})


func test_unconfigured_client():
	var c: SupabaseClient = autofree(SupabaseClient.new())
	assert_false(c.is_configured())
	c.url = "https://x.supabase.co"
	c.anon_key = "k"
	assert_true(c.is_configured())
