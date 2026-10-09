# Workspace sources

These are copies of the workspace's `tools/` files, supplied for inspection and rebuilding. They expect the workspace layout documented in the top-level README: the original IPA at the workspace root, tools in `tools/`, and the pinned touchHLE checkout in `reference/touchHLE/`.

Apply `../compatibility.patch` to upstream commit `d34530b52174e8a4f1fe43178cc4fb0c99506f9f`, including its git submodules. Building the runtime requires Rust, Visual Studio C++, CMake and touchHLE's documented dependencies. Building the launcher requires MinGW-w64. The bundled playable executables need none of these development tools.

The game preparation script accepts only the supplied original ARMv7 executable hash. It keeps game art and audio intact and writes a separate prepared app; it does not edit the original IPA.
