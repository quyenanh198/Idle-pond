class_name SupabaseClient
extends Node
## Minimal Supabase REST client: anonymous/email auth and the save RPCs.
## Request methods are coroutines returning {"ok", "code", "data", "error"}.

const CONFIG_PATH := "res://config/supabase.cfg"
const SESSION_PATH := "user://session.cfg"
const TIMEOUT_SEC := 10.0

signal _session_ensured(ok: bool)

var url := ""
var anon_key := ""
var session: Dictionary = {}
var session_path := SESSION_PATH
var _ensuring := false


func _ready() -> void:
	load_config(CONFIG_PATH)
	_load_session()


func load_config(path: String) -> void:
	var cfg := ConfigFile.new()
	if cfg.load(path) == OK:
		url = str(cfg.get_value("supabase", "url", "")).trim_suffix("/")
		anon_key = str(cfg.get_value("supabase", "anon_key", ""))


func is_configured() -> bool:
	return url != "" and anon_key != ""


func is_signed_in() -> bool:
	return session.has("access_token")


## Makes sure there is a valid session: refreshes or signs in as a guest. False if offline.
## Concurrent callers share one attempt, so two callers never create two guest accounts.
func ensure_session() -> bool:
	if _ensuring:
		return await _session_ensured
	_ensuring = true
	var ok: bool = await _ensure_session()
	_ensuring = false
	_session_ensured.emit(ok)
	return ok


func _ensure_session() -> bool:
	if not is_configured():
		return false
	if not is_signed_in():
		return await sign_in_anonymously()
	if Time.get_unix_time_from_system() < float(session.get("expires_at", 0.0)) - 60.0:
		return true
	var res: Dictionary = await refresh_session()
	if res.ok:
		return true
	if res.code >= 400 and res.code < 500:
		# Refresh token rejected: start a new guest; local progress is uploaded on next sync.
		_set_session({})
		return await sign_in_anonymously()
	return false


func sign_in_anonymously() -> bool:
	var res: Dictionary = await _request(HTTPClient.METHOD_POST, "/auth/v1/signup", {}, false)
	return _store_auth(res).ok


func refresh_session() -> Dictionary:
	var body := {"refresh_token": session.get("refresh_token", "")}
	var res: Dictionary = await _request(HTTPClient.METHOD_POST, "/auth/v1/token?grant_type=refresh_token", body, false)
	return _store_auth(res)


func sign_in_with_password(email: String, password: String) -> Dictionary:
	var body := {"email": email, "password": password}
	var res: Dictionary = await _request(HTTPClient.METHOD_POST, "/auth/v1/token?grant_type=password", body, false)
	return _store_auth(res)


## Attaches an email to the current (guest) user. Supabase emails a confirmation link.
func link_email(email: String) -> Dictionary:
	return await _request(HTTPClient.METHOD_PUT, "/auth/v1/user", {"email": email})


func set_password(password: String) -> Dictionary:
	return await _request(HTTPClient.METHOD_PUT, "/auth/v1/user", {"password": password})


func get_user() -> Dictionary:
	return await _request(HTTPClient.METHOD_GET, "/auth/v1/user")


func sign_out() -> Dictionary:
	var res: Dictionary = await _request(HTTPClient.METHOD_POST, "/auth/v1/logout")
	_set_session({})
	return res


func save_game(state: Dictionary, save_version: int, lifetime_coins: float) -> Dictionary:
	var body := {"p_data": state, "p_save_version": save_version, "p_lifetime_coins": lifetime_coins}
	return await _request(HTTPClient.METHOD_POST, "/rest/v1/rpc/save_game", body)


func load_game() -> Dictionary:
	return await _request(HTTPClient.METHOD_POST, "/rest/v1/rpc/load_game", {})


static func parse_response(result: int, code: int, body: PackedByteArray) -> Dictionary:
	if result != HTTPRequest.RESULT_SUCCESS:
		return {"ok": false, "code": code, "data": null, "error": "network error %d" % result}
	var data: Variant = null
	var json := JSON.new()
	if json.parse(body.get_string_from_utf8()) == OK:
		data = json.data
	var ok := code >= 200 and code < 300
	return {"ok": ok, "code": code, "data": data, "error": "" if ok else _error_message(data, code)}


static func session_from_auth(data: Variant, now: float) -> Dictionary:
	if typeof(data) != TYPE_DICTIONARY or not data.has("access_token"):
		return {}
	var user: Dictionary = data.user if typeof(data.get("user")) == TYPE_DICTIONARY else {}
	return {
		"access_token": str(data.access_token),
		"refresh_token": str(data.get("refresh_token", "")),
		"expires_at": now + float(data.get("expires_in", 3600)),
		"user_id": str(user.get("id", "")),
	}


static func _error_message(data: Variant, code: int) -> String:
	if typeof(data) == TYPE_DICTIONARY:
		for key in ["msg", "message", "error_description", "error"]:
			if data.has(key):
				return str(data[key])
	return "HTTP %d" % code


func _request(method: int, path: String, body: Variant = null, use_session := true) -> Dictionary:
	var http := HTTPRequest.new()
	http.timeout = TIMEOUT_SEC
	add_child(http)
	var token: String = session.get("access_token", anon_key) if use_session else anon_key
	var headers := PackedStringArray([
		"apikey: " + anon_key,
		"Authorization: Bearer " + token,
		"Content-Type: application/json",
	])
	var payload := "" if body == null else JSON.stringify(body)
	var err := http.request(url + path, headers, method, payload)
	if err != OK:
		http.queue_free()
		return {"ok": false, "code": 0, "data": null, "error": "request failed %d" % err}
	var res: Array = await http.request_completed
	http.queue_free()
	return parse_response(res[0], res[1], res[3])


func _store_auth(res: Dictionary) -> Dictionary:
	if res.ok:
		var s := session_from_auth(res.data, Time.get_unix_time_from_system())
		if s.is_empty():
			res.ok = false
			res.error = "unexpected auth response"
		else:
			_set_session(s)
	return res


func _set_session(s: Dictionary) -> void:
	session = s
	var cfg := ConfigFile.new()
	for key in s:
		cfg.set_value("session", key, s[key])
	cfg.save(session_path)


func _load_session() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(session_path) != OK or not cfg.has_section("session"):
		return
	for key in cfg.get_section_keys("session"):
		session[key] = cfg.get_value("session", key)
