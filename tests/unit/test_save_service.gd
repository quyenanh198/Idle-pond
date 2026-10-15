extends GutTest

const SaveServiceScript := preload("res://scripts/autoload/save_service.gd")
const PATH := "user://test_save.json"

var svc


func before_each():
	svc = autofree(SaveServiceScript.new())
	svc.local_path = PATH
	GameState.reset()


func after_each():
	DirAccess.remove_absolute(ProjectSettings.globalize_path(PATH))
	GameState.reset()


func test_local_round_trip():
	GameState.coins = 1234.0
	GameState.owned = {"guppy": 3}
	svc.save_local()
	GameState.reset()
	var env: Dictionary = svc.read_local()
	GameState.load_dict(env.state)
	assert_eq(GameState.coins, 1234.0)
	assert_eq(GameState.owned, {"guppy": 3})
	assert_almost_eq(env.saved_at, Time.get_unix_time_from_system(), 5.0)


func test_missing_or_corrupt_file_reads_empty():
	assert_eq(svc.read_local(), {})
	var f := FileAccess.open(PATH, FileAccess.WRITE)
	f.store_string("{broken")
	f.close()
	assert_eq(svc.read_local(), {})
