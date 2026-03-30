speaker

[Petri Purho](https://braindump.jethro.dev/posts/petri_purho)

company

[Nolla Games](https://braindump.jethro.dev/posts/nolla_games)

tags

[[posts-game-design|Game Design]]

Noita uses a very simple falling sand simulation algorithm, liquids and gases are implemented similarly.

Rigid bodies use a marching square algorithm.

How to simulate all pixels in a big world? Multi-threading! The world is divided into \\(64 \\times 64\\) chunks. Each chunk keeps a dirty rectangle, containing all the pixels that need to be simulated.
