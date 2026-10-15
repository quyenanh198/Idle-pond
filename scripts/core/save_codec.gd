class_name SaveCodec
## Save file format, migrations, and the rules for choosing between saves.

const CURRENT_VERSION := 1


static func encode(state: Dictionary, saved_at: float) -> String:
	return JSON.stringify({"save_version": CURRENT_VERSION, "saved_at": saved_at, "state": state})


## Returns the migrated envelope, or {} if text is not a usable save.
static func decode(text: String) -> Dictionary:
	var json := JSON.new()
	if json.parse(text) != OK:
		return {}
	var parsed = json.data
	if typeof(parsed) != TYPE_DICTIONARY:
		return {}
	if typeof(parsed.get("state")) != TYPE_DICTIONARY:
		return {}
	return migrate(parsed)


## Upgrades an envelope to CURRENT_VERSION one step at a time.
## Add a step per version bump, e.g. `if version == 1: envelope = _v1_to_v2(envelope); version = 2`.
## Returns {} for saves written by a newer build.
static func migrate(envelope: Dictionary) -> Dictionary:
	var version := int(envelope.get("save_version", 1))
	if version > CURRENT_VERSION:
		return {}
	envelope.save_version = version
	return envelope


## Converts the load_game RPC result (array of rows) into an envelope.
static func from_cloud_rows(rows: Variant) -> Dictionary:
	if typeof(rows) != TYPE_ARRAY or rows.is_empty() or typeof(rows[0]) != TYPE_DICTIONARY:
		return {}
	var row: Dictionary = rows[0]
	if typeof(row.get("data")) != TYPE_DICTIONARY:
		return {}
	return migrate({
		"save_version": int(row.get("save_version", 1)),
		"state": row.data,
		"elapsed_seconds": float(row.get("elapsed_seconds", 0.0)),
	})


## Which save to keep: the one with more lifetime coins. Tie keeps local.
static func pick(local: Dictionary, cloud: Dictionary) -> String:
	if local.is_empty() and cloud.is_empty():
		return ""
	if cloud.is_empty():
		return "local"
	if local.is_empty():
		return "cloud"
	return "cloud" if _lifetime(cloud) > _lifetime(local) else "local"


## Seconds the player was away. Server time is trusted over the device clock.
static func offline_elapsed(source: String, local: Dictionary, cloud: Dictionary, now: float) -> float:
	if source == "cloud":
		return maxf(float(cloud.get("elapsed_seconds", 0.0)), 0.0)
	if source == "local":
		var device := maxf(now - float(local.get("saved_at", now)), 0.0)
		if cloud.has("elapsed_seconds"):
			return minf(device, maxf(float(cloud.elapsed_seconds), 0.0))
		return device
	return 0.0


static func _lifetime(envelope: Dictionary) -> float:
	return float(envelope.state.get("lifetime_coins", 0.0))
