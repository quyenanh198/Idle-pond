extends GutTest


func test_small_values():
	assert_eq(NumberFormat.short(0.0), "0")
	assert_eq(NumberFormat.short(0.5), "0.5")
	assert_eq(NumberFormat.short(12.7), "12")
	assert_eq(NumberFormat.short(999.0), "999")


func test_suffixes_round_down():
	assert_eq(NumberFormat.short(1000.0), "1.0K")
	assert_eq(NumberFormat.short(1299.0), "1.2K")
	assert_eq(NumberFormat.short(3.45e6), "3.4M")
	assert_eq(NumberFormat.short(5.67e9), "5.6B")
	assert_eq(NumberFormat.short(7.85e12), "7.8T")
	assert_eq(NumberFormat.short(1.55e15), "1550.0T")
