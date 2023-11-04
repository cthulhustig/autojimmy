#!/usr/bin/env python3
import autojimmy
import multiprocessing

if __name__ == "__main__":
    # This is required for multiprocessing to work with apps that have been frozen as Windows exes.
    # This needs to be called as the first line of the script
    # https://docs.python.org/3/library/multiprocessing.html#windows
    multiprocessing.freeze_support()

    autojimmy.main()
