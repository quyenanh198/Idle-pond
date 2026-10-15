extends Control
## Side-view aquarium: water shader, sand and seaweed, bubbles, and the fish.

const FishScript := preload("res://scripts/pond/fish.gd")
const WaterShader := preload("res://shaders/water.gdshader")
## Vertical band (fraction of height) each zone's fish swim in.
const BANDS := {
	SpeciesData.Zone.SURFACE: Vector2(0.08, 0.30),
	SpeciesData.Zone.MID: Vector2(0.36, 0.62),
	SpeciesData.Zone.BOTTOM: Vector2(0.74, 0.86),
}

var _decor: Control
var _fish_layer: Node2D
var _bubbles: CPUParticles2D
var _time := 0.0


func _ready() -> void:
	clip_contents = true
	mouse_filter = MOUSE_FILTER_IGNORE
	var water := ColorRect.new()
	water.set_anchors_preset(PRESET_FULL_RECT)
	water.mouse_filter = MOUSE_FILTER_IGNORE
	var mat := ShaderMaterial.new()
	mat.shader = WaterShader
	water.material = mat
	add_child(water)
	_decor = Control.new()
	_decor.set_anchors_preset(PRESET_FULL_RECT)
	_decor.mouse_filter = MOUSE_FILTER_IGNORE
	_decor.draw.connect(_draw_decor)
	add_child(_decor)
	_fish_layer = Node2D.new()
	add_child(_fish_layer)
	_bubbles = _make_bubbles()
	add_child(_bubbles)
	resized.connect(_on_resized)
	GameState.changed.connect(_sync_fish)
	_on_resized()


func _process(delta: float) -> void:
	_time += delta
	_decor.queue_redraw()


## How many of each species to draw, keeping the total at or under `cap`
## and every owned species visible at least once.
static func render_counts(owned: Dictionary, cap: int) -> Dictionary:
	var kinds := []
	var total := 0
	for id in owned:
		if int(owned[id]) > 0:
			kinds.append(id)
			total += int(owned[id])
	var result := {}
	if total <= cap:
		for id in kinds:
			result[id] = int(owned[id])
		return result
	var rest := cap - kinds.size()
	var used := 0
	for id in kinds:
		result[id] = 1 + floori(float(owned[id]) * rest / total)
		used += result[id]
	kinds.sort_custom(func(a, b): return int(owned[a]) > int(owned[b]))
	var i := 0
	while used < cap:
		result[kinds[i % kinds.size()]] += 1
		used += 1
		i += 1
	return result


func band_rect(zone: int) -> Rect2:
	var b: Vector2 = BANDS[zone]
	return Rect2(size.x * 0.06, size.y * b.x, size.x * 0.88, size.y * (b.y - b.x))


func _on_resized() -> void:
	_bubbles.position = Vector2(size.x / 2.0, size.y * 0.9)
	_bubbles.emission_rect_extents = Vector2(size.x * 0.45, 4.0)
	for f in _fish_layer.get_children():
		f.band = band_rect(f.species.zone)
		f.position = f.position.clamp(f.band.position, f.band.end)
	_sync_fish()


func _sync_fish() -> void:
	if size.x <= 0.0 or size.y <= 0.0:
		return
	var want := render_counts(GameState.owned, Balance.MAX_RENDERED_FISH)
	var have := {}
	for f in _fish_layer.get_children():
		if not f.is_queued_for_deletion():
			have.get_or_add(f.species.id, []).append(f)
	for s in SpeciesCatalog.all():
		var list: Array = have.get(s.id, [])
		var n := int(want.get(s.id, 0))
		while list.size() > n:
			list.pop_back().queue_free()
		while list.size() < n:
			var f := FishScript.new()
			_fish_layer.add_child(f)
			f.setup(s, band_rect(s.zone))
			list.append(f)


func _draw_decor() -> void:
	var w := size.x
	var h := size.y
	var sand_top := h * 0.88
	var sand := PackedVector2Array([Vector2(0.0, h)])
	for i in 9:
		sand.append(Vector2(w * i / 8.0, sand_top + sin(i * 1.7) * 6.0))
	sand.append(Vector2(w, h))
	_decor.draw_colored_polygon(sand, Color(0.86, 0.76, 0.52))
	for i in 6:
		var base := Vector2(w * (0.1 + i * 0.16), sand_top + 4.0)
		var weed := PackedVector2Array()
		for k in 8:
			weed.append(Vector2(base.x + sin(_time * 1.5 + i + k * 0.5) * k * 2.5, base.y - k * h * 0.035))
		_decor.draw_polyline(weed, Color(0.2, 0.6, 0.3), 5.0, true)
	_decor.draw_circle(Vector2(w * 0.3, sand_top + 6.0), 14.0, Color(0.5, 0.5, 0.55))
	_decor.draw_circle(Vector2(w * 0.72, sand_top + 8.0), 20.0, Color(0.45, 0.45, 0.5))


func _make_bubbles() -> CPUParticles2D:
	var p := CPUParticles2D.new()
	p.amount = 24
	p.lifetime = 6.0
	p.preprocess = 6.0
	p.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	p.direction = Vector2.UP
	p.spread = 8.0
	p.gravity = Vector2(0.0, -20.0)
	p.initial_velocity_min = 30.0
	p.initial_velocity_max = 60.0
	p.scale_amount_min = 2.0
	p.scale_amount_max = 5.0
	p.color = Color(1.0, 1.0, 1.0, 0.35)
	return p
