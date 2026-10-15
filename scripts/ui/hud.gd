extends PanelContainer
## Coins, income, level bar, cloud status and a level-up toast. Refreshes 10×/s.

const CLOUD_TEXT := {"off": "", "syncing": "Syncing…", "ok": "Saved", "error": "Offline"}

var _coins: Label
var _income: Label
var _level: Label
var _xp: ProgressBar
var _cloud: Label
var _toast: Label
var _accum := 0.0


func _ready() -> void:
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.13, 0.15, 0.18)
	style.set_content_margin_all(12)
	add_theme_stylebox_override("panel", style)
	var v := VBoxContainer.new()
	add_child(v)
	var top := HBoxContainer.new()
	v.add_child(top)
	_coins = Label.new()
	_coins.size_flags_horizontal = SIZE_EXPAND_FILL
	_coins.add_theme_font_size_override("font_size", 38)
	top.add_child(_coins)
	_income = Label.new()
	top.add_child(_income)
	var bar := HBoxContainer.new()
	v.add_child(bar)
	_level = Label.new()
	bar.add_child(_level)
	_xp = ProgressBar.new()
	_xp.size_flags_horizontal = SIZE_EXPAND_FILL
	_xp.size_flags_vertical = SIZE_SHRINK_CENTER
	_xp.custom_minimum_size.y = 18
	_xp.show_percentage = false
	bar.add_child(_xp)
	_cloud = Label.new()
	_cloud.add_theme_font_size_override("font_size", 20)
	bar.add_child(_cloud)
	_toast = Label.new()
	_toast.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_toast.modulate.a = 0.0
	v.add_child(_toast)
	GameState.leveled_up.connect(_on_leveled_up)
	SaveService.cloud_status_changed.connect(func(s: String): _cloud.text = CLOUD_TEXT[s])
	_cloud.text = CLOUD_TEXT[SaveService.cloud_status]
	_refresh()


func _process(delta: float) -> void:
	_accum += delta
	if _accum >= 0.1:
		_accum = 0.0
		_refresh()


func _refresh() -> void:
	_coins.text = "%s coins" % NumberFormat.short(GameState.coins)
	_income.text = "+%s/s" % NumberFormat.short(GameState.income_per_sec())
	var p := GameState.level_progress()
	_level.text = "Lv %d " % p.level
	_xp.max_value = p.needed
	_xp.value = p.into


func _on_leveled_up(level: int) -> void:
	var names := PackedStringArray()
	for s in SpeciesCatalog.all():
		if s.unlock_level == level:
			names.append(s.display_name)
	_toast.text = "Level %d!" % level
	if not names.is_empty():
		_toast.text += "  New species: " + ", ".join(names)
	_toast.modulate.a = 1.0
	create_tween().tween_property(_toast, "modulate:a", 0.0, 2.5).set_delay(1.5)
