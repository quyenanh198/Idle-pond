class_name NumberFormat

const SUFFIXES := ["", "K", "M", "B", "T"]


## Short display: 0.5, 12, 1.2K, 3.4M. Rounds down so it never shows more than you have.
static func short(value: float) -> String:
	if value < 1000.0:
		if value < 10.0 and not is_equal_approx(value, floorf(value)):
			return "%.1f" % (floorf(value * 10.0) / 10.0)
		return str(floori(value))
	var tier := 0
	var scaled := value
	while scaled >= 1000.0 and tier < SUFFIXES.size() - 1:
		scaled /= 1000.0
		tier += 1
	return "%.1f%s" % [floorf(scaled * 10.0) / 10.0, SUFFIXES[tier]]
