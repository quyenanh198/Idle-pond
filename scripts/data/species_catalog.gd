class_name SpeciesCatalog
## All species, sorted by unlock level. Explicit paths so exports never miss a file.

const PATHS := [
	"res://data/species/guppy.tres",
	"res://data/species/snail.tres",
	"res://data/species/goldfish.tres",
	"res://data/species/tetra.tres",
	"res://data/species/catfish.tres",
	"res://data/species/angelfish.tres",
	"res://data/species/koi.tres",
	"res://data/species/arowana.tres",
]

static var _cache: Array[SpeciesData] = []


static func all() -> Array[SpeciesData]:
	if _cache.is_empty():
		for path in PATHS:
			_cache.append(load(path) as SpeciesData)
		_cache.sort_custom(func(a, b): return a.unlock_level < b.unlock_level)
	return _cache


static func by_id(id: String) -> SpeciesData:
	for s in all():
		if s.id == id:
			return s
	return null
