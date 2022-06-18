# Gatari Lines Extractor
These scripts are designed to extract frames based on subtitles, one frame per subtitle, and
generate files that can be fed to a Twitter bot. Technically designed to handle the Monogatari
series, but could be used in any instance that needs subtitles extracted in-order.

Some of this code is "borrowed" from an in-progress work to make a bot that extracts lines from
all Shaft series, which were in turn "borrowed" from the original scripts to extract from Monogatari.
These are revamped here with better documentation. And will probably be fed back to the Shaft 
extractor when I get around to working on that. I was going to bring the gatari bot over to my
bot framework 

## Required Software
The scripts use some Python 3.10 features, so that needs to be installed:

```
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.10 python3.10-venv
```

`mkvmerge` needs to be on the path. Under ubuntu this is provided by the package `mkvtoolnix`.

## File Structure

This script is designed to be pointed at a directory with the following layout:

- /mediainfo - Destination path for extracted bits and bobs from the mkv files.
- /source - contains directories per series containing video files, and episode information

### `/source`

This contains one directory per series, prefixed with a number so when sorted, they end up in the
proper order. Currently that order is:

> 01 Bakemonogatari
> 01.5 Kizumonogatari
> 02 Nisemonogatari
> 03 Nekomonogatari (Black)
> 04 Monogatari Series Second Season
> - Arc 01 Nekomonogatari Shiro
> - Arc 02 Kabukimonogatari
> - Arc 03 Otorimonogatari
> - Arc 04 Onimonogatari
> - Arc 05 Koimonogatari
> - Arc 06 Hanamonogatari
> 05 Tsukimonogatari
> 06 Owarimonogatari
> 07 Koyomimonogatari
> 08 Owarimonogatari S2
> 09 Zoku Owarimonogatari

I don't recall why Kizu is number 1.5, or why I kept the directories under Second Season. I'm sure
I had a good reason two years ago and didn't write it down. 

In this directory this run `find -iname "*.mkv" | sort` to get a list of all files. With my set of
media as of this writing, `find -iname "*.mkv" | wc -l` returns 105 and [Wikipedia](https://en.wikipedia.org/wiki/List_of_Monogatari_episodes)
lists 103 episodes. The discrepancy is from the version of Hanamonogatari I have using linked chapters
(WHY) for its OP and ED. This check is important because this writeup is happening because for two
years I never noticed I was missing Owari S2. And I'm sure some new Monogatari series will be animated
at some point, even though its been three years.

If the sorted file list looks fine, pipe it to a text file for any cleanups (like removing linked chapters),
otherwise adjust directory and file names so they look right. From this text file, make a CSV with
the following columns:

- File Name: Output from the `find` command
- Series Order: The overall ordering of the series
- Series Name: The name of the series, this will eventually go into the tweets by the bot.
- Episode Number: Order within the series. This will go into the tweets.
- Overall Order: What controls the ordering of the episodes for tweets

## Scripts
The scripts are listed in the order they should be run to go from a bunch of loose video files to
extracted frames and loading the data into an Azure table.

### `extract_attachments.py`
Reads a list of files from a CSV file called `Episodes.csv` in the source directory. For each file in
the CSV, it runs `mkvmerge --identify -J` on it and parses the JSON it returns. It saves this JSON
to a file called `mediainfo.json` in a directory under the mediainfo directory named for the input
file name stripped of its extension.

It then calls `mkvextract` to dump out all subtitles and fonts from the input file. These are
stored in directories called `subs` and `fonts` respectively. It then writes a file called 
`episode_info.json` that contains information for that episode from the `Episodes.csv` file, along
with path information for the original file and the base directory for that episode in mediainfo.

Additionally, a `subs.json` is written that contains information for each subtitle file written into
the `subs` directory. This contains the full path the the subtitle file, its language and track number,
along with its info from the output of `mkvmerge`.

Finally it touches a file named `.completed` in the mediainfo directory that will cause the input
file to be skipped if it exists, to prevent reprocessing of media files.

The fonts extracted aren't always needed for subtitle extraction. If ffmpeg throws a fit over finding
fonts, all the fonts can be copied to the `~/.fonts` directory, where it will pick them up with an
appropriate fontconfig file.

### `process_subs.py`
Looks for `episode_info.json` files in the mediainfo directory, it loads the sibling `subs.json` file
in the same folder.

Each subtitle file in `subs.json` is read in. It first strips any escape sequences and text in curly
braces in the subtitle text. It then takes this text, and if it is purely CJK text, removes all spaces
from it. If it is latin text, it collapses all whitespace characters down to a single space. Finally
it sorts the subtitles by their starting time.

After that, some horrible code. It looks through all of the subtitles for ones that have the same 
text, and have a start time that matches a previous lines ending time, for example:
```csv
Start,End,Text
0:17:24.65,0:17:24.69,Weight
0:17:24.69,0:17:24.74,Weight
0:17:24.74,0:17:24.78,Weight
0:17:24.78,0:17:24.82,Weight
```
It looks for runs like this and combines them into one subtitle where the start is the earliest in
the sequence, and the end is the latest in the sequence, so `0:17:24.65,0:17:24.82,Weight` in this 
example. This is currently horrible because for every subtitle, it looks through _all_ of the subtitles
in the current file, and for each of those also through a list of ones it has already seen. 

Finally it takes all subtitles that start at the same time and combines them into one "line".

Once this is done it writes out a JSON file containing the path of the original ASS subs, the subtitle
processor version, and the list of subtitles.

The subtitle version field is used to detect if subtitles should be re-processed, if changes are made.
This is done by changing the value of `SUB_VERSION` at the top of the file. If a subtitle JSON file 
exists in the subtitle directory, and it is the same as the current version, the processing is skipped.


### `grab_frames.py`
Looks for `episode_info.json` files in the mediainfo directory. It reads in the episode_info file,
and the subtitle file to figure out which processed subtitle file to use.

It then uses the `av` library, which is a wrapper around ffmpeg to open the source video, configure
it to burn the subtitles into the video frame with a filter graph, and then decode frames as fast
as possible.

Each frame decoded is checked to see if its time matches the next subtitle time, defined as the 
halfway point between the start of a subtitle and its end. If the frame time is at least or past the
subtitle time, it is saved out to the frames directory.

Once a video has completed playback, a file containing a mapping between the saved frame files names
and the subtitles is written out to the frame directory called `frame_info.json`. This file is 
checked for before opening the video file to determine if the video should be skipped.

### `generate_preview_html.py`
Simple script that looks through the frame directories for `frame_info.json`, and if it finds it,
uses Jinja to generate an HTML file that displays all of the frames next to the subtitle text.

### `load_to_azure.py`
Expects a `AZURE_TABLE_URL` environment variable to be set that is a URL to a specific Azure Storage
Table with a SAS token. The SAS token must at least have write privileges.

Loads all the `frame_info.json` files from the frames directory, and orders them by the Overall Order
that was provided in the initial CSV to this pipeline, and then by when the frame was extracted. It
massages the data slightly to generate `PartitionKey` and `RowKey` fields that Tables expect. Then it
sets `NextPartitionKey` and `NextRowKey` for each item to the one of the next item in the list, with
the very last item using the partition and row keys of the first item, effectively making a circular
linked list.

Finally it shoves all of these into an Azure table.