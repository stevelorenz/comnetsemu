all: release

release:
	meson build --buildtype=release
	cd ./build && ninja

debug:
	meson -Db_sanitize=address,undefined build --buildtype=debug
	cd ./build && ninja

clean:
	rm -rf ./build

.PHONY: release debug clean
