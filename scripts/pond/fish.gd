extends Node2D
## One fish wandering inside its depth band. Placeholder art drawn in _draw().

var species: SpeciesData
var band := Rect2()
var _speed := 40.0
var _target := Vector2.ZERO
var _t := 0.0


func setup(s: SpeciesData, area: Rect2) -> void:
	species = s
	band = area
	position = _random_point()
	_target = _random_point()
	_speed = randf_range(25.0, 55.0) * (0.4 if s.zone == SpeciesData.Zone.BOTTOM else 1.0)
	_t = randf() * TAU


func _process(delta: float) -> void:
	_t += delta
	var to := _target - position
	if to.length() < 6.0 or not band.grow(1.0).has_point(_target):
		_target = _random_point()
	else:
		var dir := to.normalized()
		position += dir * _speed * delta
		if absf(dir.x) > 0.1:
			scale.x = signf(dir.x)
	queue_redraw()


func _draw() -> void:
	var size := species.body_size
	if species.sprite:
		draw_texture_rect(species.sprite, Rect2(-size / 2.0, size), false)
		return
	var wiggle := sin(_t * 8.0) * size.y * 0.25
	var tail := PackedVector2Array([
		Vector2(-size.x * 0.4, 0.0),
		Vector2(-size.x * 0.75, -size.y * 0.5 + wiggle),
		Vector2(-size.x * 0.75, size.y * 0.5 + wiggle),
	])
	draw_colored_polygon(tail, species.color.darkened(0.2))
	draw_set_transform(Vector2.ZERO, 0.0, Vector2(1.0, size.y / size.x))
	draw_circle(Vector2.ZERO, size.x * 0.5, species.color)
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	draw_circle(Vector2(size.x * 0.28, -size.y * 0.1), maxf(size.y * 0.12, 1.5), Color.BLACK)


func _random_point() -> Vector2:
	return Vector2(randf_range(band.position.x, band.end.x), randf_range(band.position.y, band.end.y))
