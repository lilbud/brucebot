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
- 2024-09-23 - added venue search command `!venue` or `!v`
- 2024-09-23 - changed song FTS to 'simple', as for unknown reasons the generated vector column was ignoring the song name on some rows.
- 2024-10-01 - added command line argument to specify the database to connect to. When running locally I use the local database, and when deployed it should use Heroku instead.
- 2024-10-08 - Updated a number of commands. Reason being is that I made some major changes to the database in regards to structure. Commands updated: album, bootleg, location, on_this_day, setlist, song, venue.
- 2024-10-10 - fixed info command, was broken after the update mentioned above.
- 2024-10-11 - fixed song command, had similarity in the wrong order and it wasn't catching inputs like 'hope and dreams'
- 2023-10-16 - further database updates, forgot to change the setlist command to match. So the tour was showing the ID instead of the tour name itself.