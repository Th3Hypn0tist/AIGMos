## General rules

full posix toolset
goal: smooth & fast render

##terminal
tH (terminal height) int
tW (terminal width) int
render frame to the terminal

##layout instance
handle (unique) string
title (free & optional parameter) string
buffer string
command_history list(indexed)
frame string
- builds whole layout as one frame

## rows & cells
h (optional height in %) int 
w (optional widht in %) int
va (optional vertical align for middle and top, bottom is default) string
- cells and rows calculate relative size from tH and tW. tW: 90, 3cells > every cell gets 33% (100%/3cells) > cell width: 30.
- if h or w set then calculate that away: 3 cells and one has w=5. Rest two > 95%/2cells = tH 80 > cell1: 38, cell2: 38 cell3: 4 total: 80

##layout module instance
parent (layout instance handle) string
name (unique for the parent) string
focusable bool (for text scroll etc)

- module also has own variables
- can take <cs> input if not parsed as command or symbol set. (like <q>)
- returns only string element to be parsed to the layout.

