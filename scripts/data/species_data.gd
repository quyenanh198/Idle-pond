class_name SpeciesData
extends Resource
## One fish species. Values are tuned in data/species/*.tres.

enum Zone { SURFACE, MID, BOTTOM }

@export var id: String = ""
@export var display_name: String = ""
@export var unlock_level: int = 1
@export var base_cost: float = 10.0
@export var coins_per_sec: float = 0.5
@export var zone: Zone = Zone.MID
## Placeholder art: body color and size used when no sprite is set.
@export var color: Color = Color.WHITE
@export var body_size: Vector2 = Vector2(40, 20)
@export var sprite: Texture2D
