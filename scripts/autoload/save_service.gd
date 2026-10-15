extends Node
## Local + cloud persistence. Autoloaded as `SaveService`; Main calls start() once.

signal offline_earned(amount: float)
signal cloud_status_changed(status: String)

const LOCAL_PATH := "user://save.json"
const LOCAL_INTERVAL_SEC := 10.0
const CLOUD_INTERVAL_SEC := 60.0

var client: SupabaseClient
var local_path := LOCAL_PATH
var cloud_status := "off"
var _started := false
var _cloud_busy := false


func _ready() -> void:
	client = SupabaseClient.new()
	add_child(client)


## Startup flow from spec section 4: local first, then cloud, then offline earnings.
func start() -> void:
	var local := read_local()
	if not local.is_empty():
		GameState.load_dict(local.state)
	GameState.running = true
	_started = true
	_add_timer(LOCAL_INTERVAL_SEC, save_local)
	_add_timer(CLOUD_INTERVAL_SEC, sync_cloud)
	GameState.species_first_bought.connect(func(_id: String): sync_cloud())

	var cloud := {}
	if client.is_configured():
		_set_status("syncing")
		if await client.ensure_session():
			var res: Dictionary = await client.load_game()
			if res.ok:
				cloud = SaveCodec.from_cloud_rows(res.data)
		_set_status("ok" if client.is_signed_in() else "error")
	var source := SaveCodec.pick(local, cloud)
	if source == "cloud":
		GameState.load_dict(cloud.state)
	var elapsed := SaveCodec.offline_elapsed(source, local, cloud, Time.get_unix_time_from_system())
	var earned := GameState.apply_offline(elapsed)
	save_local()
	if earned >= 1.0:
		offline_earned.emit(earned)
	sync_cloud()


func save_local() -> void:
	var f := FileAccess.open(local_path, FileAccess.WRITE)
	if f == null:
		push_warning("Could not write save: %s" % FileAccess.get_open_error())
		return
	f.store_string(SaveCodec.encode(GameState.to_dict(), Time.get_unix_time_from_system()))


func read_local() -> Dictionary:
	if not FileAccess.file_exists(local_path):
		return {}
	return SaveCodec.decode(FileAccess.get_file_as_string(local_path))


func sync_cloud() -> void:
	if _cloud_busy or not client.is_configured():
		return
	_cloud_busy = true
	_set_status("syncing")
	var ok: bool = await client.ensure_session()
	if ok:
		var res: Dictionary = await client.save_game(GameState.to_dict(), SaveCodec.CURRENT_VERSION, GameState.lifetime_coins)
		ok = res.ok
	_set_status("ok" if ok else "error")
	_cloud_busy = false


## Signs in to an existing account, then keeps whichever save has more progress.
func sign_in(email: String, password: String) -> Dictionary:
	var res: Dictionary = await client.sign_in_with_password(email, password)
	if not res.ok:
		return res
	var loaded: Dictionary = await client.load_game()
	if loaded.ok:
		var cloud := SaveCodec.from_cloud_rows(loaded.data)
		if SaveCodec.pick({"state": GameState.to_dict()}, cloud) == "cloud":
			GameState.load_dict(cloud.state)
	save_local()
	await sync_cloud()
	return res


## Signs out and starts a fresh guest pond on this device.
func sign_out() -> void:
	await client.sign_out()
	GameState.reset()
	save_local()
	await sync_cloud()


func _notification(what: int) -> void:
	if not _started:
		return
	if what in [NOTIFICATION_APPLICATION_PAUSED, NOTIFICATION_APPLICATION_FOCUS_OUT, NOTIFICATION_WM_CLOSE_REQUEST]:
		save_local()
		sync_cloud()


func _add_timer(wait: float, callback: Callable) -> void:
	var t := Timer.new()
	t.wait_time = wait
	t.autostart = true
	t.timeout.connect(callback)
	add_child(t)


func _set_status(status: String) -> void:
	if status != cloud_status:
		cloud_status = status
		cloud_status_changed.emit(status)
