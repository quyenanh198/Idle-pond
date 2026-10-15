extends GutTest


func _env(lifetime: float) -> Dictionary:
	return {"save_version": 1, "saved_at": 1000.0, "state": {"lifetime_coins": lifetime}}


func test_encode_decode_round_trip():
	var text := SaveCodec.encode({"coins": 5.0, "lifetime_coins": 9.0}, 1234.0)
	var env := SaveCodec.decode(text)
	assert_eq(env.save_version, 1)
	assert_eq(env.saved_at, 1234.0)
	assert_eq(env.state.coins, 5.0)


func test_decode_rejects_garbage_and_future_versions():
	assert_eq(SaveCodec.decode(""), {})
	assert_eq(SaveCodec.decode("{not json"), {})
	assert_eq(SaveCodec.decode("[1,2]"), {})
	assert_eq(SaveCodec.decode('{"save_version": 1}'), {})
	assert_eq(SaveCodec.decode('{"save_version": 99, "state": {}}'), {})


func test_from_cloud_rows():
	assert_eq(SaveCodec.from_cloud_rows([]), {})
	assert_eq(SaveCodec.from_cloud_rows(null), {})
	var env := SaveCodec.from_cloud_rows([{"data": {"coins": 3.0}, "save_version": 1, "lifetime_coins": 3.0, "elapsed_seconds": 42.5}])
	assert_eq(env.state.coins, 3.0)
	assert_eq(env.elapsed_seconds, 42.5)


func test_pick_prefers_more_lifetime_coins_tie_keeps_local():
	assert_eq(SaveCodec.pick({}, {}), "")
	assert_eq(SaveCodec.pick(_env(5.0), {}), "local")
	assert_eq(SaveCodec.pick({}, _env(5.0)), "cloud")
	assert_eq(SaveCodec.pick(_env(5.0), _env(9.0)), "cloud")
	assert_eq(SaveCodec.pick(_env(9.0), _env(5.0)), "local")
	assert_eq(SaveCodec.pick(_env(5.0), _env(5.0)), "local")


func test_offline_elapsed_rules():
	var local := {"saved_at": 1000.0, "state": {}}
	var cloud := {"elapsed_seconds": 300.0, "state": {}}
	assert_eq(SaveCodec.offline_elapsed("cloud", local, cloud, 5000.0), 300.0)
	assert_eq(SaveCodec.offline_elapsed("local", local, {}, 1600.0), 600.0)
	assert_eq(SaveCodec.offline_elapsed("local", local, cloud, 5000.0), 300.0, "server caps device clock")
	assert_eq(SaveCodec.offline_elapsed("local", local, cloud, 1100.0), 100.0)
	assert_eq(SaveCodec.offline_elapsed("local", local, {}, 500.0), 0.0, "clock set backwards")
	assert_eq(SaveCodec.offline_elapsed("", {}, {}, 500.0), 0.0)
