# CHANGELOG
### This changelog was part of the README, but its now moved to its own file.

- 2024-07-30 - Initial commit, almost all features from Brucebot 1.0 moved over. Complete rewrite of bot from scratch, largely due to a rewrite of the Databruce project.
- 2024-08-04 - fixed none short_name breaking song embed
- 2024-08-04 - fixed tour not showing up
- 2024-08-04 - fixed incorrect footer on help command (showing bbhelp instead of bhelp)
- 2024-08-04 - fixed tour opener/closer count, was counting soundchecks/rehearsals by accident
- 2024-08-04 - removed timeout on stats embed menu
- 2024-08-04 - add aliases to song search
- 2024-08-16 - update cover finder. Add nugs covers as a fallback if I don't have a cover made for a show that got Nugs release
- 2024-08-16 - fix archive links not having the archive.org url
- 2024-08-21 - fix song search. Had issue with the search ranking, so "Into The Fire" was actually pulling up the first result which was Hendrix's Fire. Switched Rank and Similarity in the ORDER BY, seems to have fixed it.
- 2024-09-08 - remove timeout on covers embed viewmenu