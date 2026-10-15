extends VBoxContainer
## The three pond upgrades.

var _rows := {}  # upgrade id -> {"info": Label, "button": Button}
var _accum := 0.0


func _ready() -> void:
	for id in Balance.UPGRADES:
		var row := HBoxContainer.new()
		add_child(row)
		var info := Label.new()
		info.size_flags_horizontal = SIZE_EXPAND_FILL
		row.add_child(info)
		var button := Button.new()
		button.custom_minimum_size.x = 220
		button.pressed.connect(GameState.upgrade.bind(id))
		row.add_child(button)
		_rows[id] = {"info": info, "button": button}
	GameState.changed.connect(_refresh)
	_refresh()


func _process(delta: float) -> void:
	_accum += delta
	if _accum >= 0.25:
		_accum = 0.0
		_refresh()


func _refresh() -> void:
	for id in _rows:
		var r: Dictionary = _rows[id]
		var n := GameState.upgrade_level(id)
		var maxed := Economy.upgrade_maxed(id, n)
		r.info.text = "%s (Lv %d)\n%s" % [Balance.UPGRADES[id].name, n, effect_text(id, n, maxed)]
		r.button.text = "Max" if maxed else "Upgrade %s" % NumberFormat.short(GameState.upgrade_cost(id))
		r.button.disabled = not GameState.can_upgrade(id)


static func effect_text(id: String, n: int, maxed: bool) -> String:
	match id:
		Balance.POND_SIZE:
			return "Capacity %d → %d" % [Economy.capacity(n), Economy.capacity(n + 1)]
		Balance.BETTER_FOOD:
			return "Income x%.2f → x%.2f" % [Economy.food_multiplier(n), Economy.food_multiplier(n + 1)]
		Balance.DEEP_SLEEP:
			var hours := int(Economy.offline_cap_sec(n) / 3600.0)
			if maxed:
				return "Offline earnings up to %dh" % hours
			return "Offline earnings up to %dh → %dh" % [hours, int(Economy.offline_cap_sec(n + 1) / 3600.0)]
	return ""
