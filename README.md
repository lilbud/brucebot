# Brucebot
Discord bot that works with my Databruce project

This repo contains the code behind the bot, the bot itself is hosted on Heroku. The code here is pretty much just for reference and as a remote for Heroku.

The bot is built using Python and Discord.py.

# Updates from Brucebot v1.0:
- I actually know what i'm doing now, mostly.
- Utilized many of the features of Discord.py like cogs, and somewhat decent error handling
- All features from that bot moved over with the exception of:
  - Jungleland result/art search: This allowed searching of Jungleland Torrents for shows, which didn't really work because many shows are either not there or dead. Replaced with a proper bootleg search.
- Code rewritten to not be an absolute mess

# Changelog
2024-08-02 - Fixed the following things over 8/1 and 8/2:
  - fixed song embed failing to send if there isn't a short_name.
  - fixed tour not showing up on setlist embed.
  - fixed incorrect footer on help command (showing bbhelp instead of bhelp).
  - fixed tour opener/closer count, was counting soundchecks/rehearsals by accident.
2024-07-30 - Initial commit, almost all features from Brucebot 1.0 moved over. Complete rewrite of bot from scratch, largely due to a rewrite of the Databruce project.
