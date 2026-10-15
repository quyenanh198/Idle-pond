extends ScrollContainer
## Buy and sell fish. Locked species show their unlock level.

var _capacity: Label
var _rows := {}  # species id -> {"info": Label, "buy": Button, "sell": Button}
var _accum := 0.0


func _ready() -> void:
	horizontal_scroll_mode = SCROLL_MODE_DISABLED
	var list := VBoxContainer.new()
	list.size_flags_horizontal = SIZE_EXPAND_FILL
	add_child(list)
	_capacity = Label.new()
	list.add_child(_capacity)
	for s in SpeciesCatalog.all():
		var row := HBoxContainer.new()
		list.add_child(row)
		var swatch := ColorRect.new()
		swatch.color = s.color
		swatch.custom_minimum_size = Vector2(36, 36)
		swatch.size_flags_vertical = SIZE_SHRINK_CENTER
		row.add_child(swatch)
		var info := Label.new()
		info.size_flags_horizontal = SIZE_EXPAND_FILL
		row.add_child(info)
		var buy := Button.new()
		buy.custom_minimum_size.x = 190
		buy.clip_text = true
		buy.pressed.connect(GameState.buy.bind(s))
		row.add_child(buy)
		var sell := Button.new()
		sell.custom_minimum_size.x = 190
		sell.clip_text = true
		sell.pressed.connect(GameState.sell.bind(s))
		row.add_child(sell)
		_rows[s.id] = {"info": info, "buy": buy, "sell": sell}
	GameState.changed.connect(_refresh)
	_refresh()


func _process(delta: float) -> void:
	_accum += delta
	if _accum >= 0.25:
		_accum = 0.0
		_refresh()


func _refresh() -> void:
	_capacity.text = "Pond: %d / %d fish" % [GameState.total_fish(), GameState.capacity()]
	for s in SpeciesCatalog.all():
		var r: Dictionary = _rows[s.id]
		if not GameState.is_unlocked(s):
			r.info.text = "%s\nUnlocks at Lv %d" % [s.display_name, s.unlock_level]
			r.buy.text = "Locked"
			r.buy.disabled = true
			r.sell.text = "Sell"
			r.sell.disabled = true
			continue
		var count := GameState.owned_count(s)
		r.info.text = "%s  x%d\n+%s/s each" % [s.display_name, count, NumberFormat.short(s.coins_per_sec)]
		r.buy.text = "Buy %s" % NumberFormat.short(GameState.fish_cost(s))
		r.buy.disabled = not GameState.can_buy(s)
		r.sell.text = ("Sell +%s" % NumberFormat.short(GameState.sell_refund(s))) if count > 0 else "Sell"
		r.sell.disabled = count == 0
