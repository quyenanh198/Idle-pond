extends GutTest
## Talks to tests/mock_supabase.py (started by run_tests.sh).

const SESSION_PATH := "user://test_session.cfg"

var client: SupabaseClient


func before_each():
	client = null
	var url := OS.get_environment("MOCK_SUPABASE_URL")
	if url == "":
		return
	client = SupabaseClient.new()
	client.session_path = SESSION_PATH
	add_child_autofree(client)
	client.url = url
	client.anon_key = "test-anon-key"
	client.session = {}


func after_each():
	DirAccess.remove_absolute(ProjectSettings.globalize_path(SESSION_PATH))


func test_guest_save_and_load_round_trip():
	if client == null:
		pending("MOCK_SUPABASE_URL not set")
		return
	assert_true(await client.ensure_session(), "anonymous sign-in")
	assert_true(client.is_signed_in())
	var saved: Dictionary = await client.save_game({"coins": 7.0, "lifetime_coins": 7.0}, 1, 7.0)
	assert_true(saved.ok, saved.error)
	var loaded: Dictionary = await client.load_game()
	assert_true(loaded.ok, loaded.error)
	var env := SaveCodec.from_cloud_rows(loaded.data)
	assert_eq(env.state.coins, 7.0)
	assert_gte(env.elapsed_seconds, 0.0)


func test_expired_session_is_refreshed():
	if client == null:
		pending("MOCK_SUPABASE_URL not set")
		return
	assert_true(await client.ensure_session())
	var old_token: String = client.session.access_token
	client.session.expires_at = 0.0
	assert_true(await client.ensure_session())
	assert_ne(client.session.access_token, old_token)


func test_bad_password_reports_error():
	if client == null:
		pending("MOCK_SUPABASE_URL not set")
		return
	var res: Dictionary = await client.sign_in_with_password("a@b.c", "wrong")
	assert_false(res.ok)
	assert_eq(res.error, "Invalid login credentials")


func test_concurrent_ensure_session_signs_up_once():
	if client == null:
		pending("MOCK_SUPABASE_URL not set")
		return
	var before := await _signups()
	var first := func(): return await client.ensure_session()
	first.call()  # not awaited: runs concurrently with the next call
	assert_true(await client.ensure_session())
	await wait_seconds(0.5)
	assert_eq(await _signups(), before + 1, "only one guest account created")


func _signups() -> int:
	var res: Dictionary = await client._request(HTTPClient.METHOD_GET, "/test/stats")
	return int(res.data.signups)
