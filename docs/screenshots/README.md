# Slide gallery

Every slide in the Plex Wrapped story, in the order they are built by
[`buildSlides()`](../../static/js/wrapped.js).

Most slides are conditional — they only appear when the underlying data exists
(no favourite actor, no actor slide). The numbers below are the positions in a
full run; a user with less history simply sees a shorter deck. The example
screenshots come from a Dutch-language run, so the copy is in Dutch.

| # | Slide | Shown when | Preview |
|---|-------|-----------|---------|
| 1 | **Welcome** (`welcome`) | Always | <img src="welcome.png" alt="Welcome slide" width="200"> |
| 2 | **Watch time** (`watch-time`) | Watch history exists | <img src="watch-time.png" alt="Total watch time" width="200"> |
| 3 | **Total plays** (`total-plays`) | Watch history exists | <img src="total-plays.png" alt="Total plays" width="200"> |
| 4 | **Films vs series** (`movies-vs-tv`) | Watch history exists | <img src="movies-vs-tv.png" alt="Films versus series donut" width="200"> |
| 5 | **Top 5 films** (`top-movies`) | At least 3 different films watched | <img src="top-movies.png" alt="Top 5 films" width="200"> |
| 6 | **Top 5 series** (`top-shows`) | 3 different series, or 2 series with more than 5 episodes, or 1 series with more than 10 episodes | <img src="top-shows.png" alt="Top 5 series" width="200"> |
| 7 | **Series depth** (`series-depth`) | More than 1 series, more than 1 season, or more than 10 episodes | <img src="series-depth.png" alt="Series depth staircase" width="200"> |
| 8 | **When you watch** (`when-you-watch`) | A busiest month, day, or hour is known | <img src="when-you-watch.png" alt="Viewing rhythm" width="200"> |
| 9 | **Favourite device** (`favorite-device`) | A favourite device is known | <img src="favorite-device.png" alt="Favourite device" width="200"> |
| 10 | **Longest streak** (`longest-streak`) | Streak of at least 3 days | <img src="longest-streak.png" alt="Longest streak" width="200"> |
| 11 | **Favourite actor** (`favorite-actor`) | TMDB returned a top actor | <img src="favorite-actor.png" alt="Favourite actor" width="200"> |
| 12 | **Top film genres** (`movie-genres`) | Film genres available, and the top 5 films slide is shown | <img src="movie-genres.png" alt="Top film genres" width="200"> |
| 13 | **Top series genres** (`show-genres`) | Series genres available, and the top 5 series slide is shown | <img src="show-genres.png" alt="Top series genres" width="200"> |
| 14 | **Server rank** (`server-rank`) | Server leaderboard data available | <img src="server-rank.png" alt="Server rank" width="200"> |
| 15 | **Server vs you** (`server-vs-you`) | Both a server top show and a personal top show exist | <img src="server-vs-you.png" alt="Server versus you" width="200"> |
| 16 | **Telegram requests** (`telegram-requests`) | Telegram request activity exists | _not captured_ |
| 17 | **Your crown** (`persona`) | Always | <img src="persona.png" alt="Persona crown" width="200"> |
| 18 | **Year summary** (`summary`) | Always | <img src="summary.png" alt="Year summary" width="200"> |

## Updating a screenshot

Open a wrapped in the browser, navigate to the slide, and capture the viewport
at mobile width. Save it over the existing file using the same name — the file
name matches the slide id used in `buildSlides()`, so the gallery keeps working
without touching this table.
