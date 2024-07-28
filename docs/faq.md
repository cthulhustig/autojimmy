# FAQ

## Why the stupid name?
It's named after my Traveller character, notorious space pirate Jimmy Brogan. Auto-Jimmy started
out as a hundred or so lines of Python that I hacked together to automate some of the things I
thought Jimmy would be doing. I'd never played Traveller before, so it seemed like a good way to
learn some of the rules. At the time, it was just a noddy script, so the name didn't really mater. I
probably spent all of 30 seconds thinking about it at the time. 50000+ lines of code and a year and a
half later, the name has stuck.

## Why the hat icon?
Somehow, Jimmy managed to come out of character creation alive and with a slugger skill of 4. The
_obvious_ choice was to lean heavily into the old west gunslinger aesthetic (massively Firefly
influenced). As the app is named after Jimmy, his hat was the natural choice for an icon.
The icon I've used is Copyright Rob Sanders and has been licensed free for non-commercial use.
https://www.iconarchive.com/show/hat-icons-by-rob-sanders/Hat-cowboy-black-icon.html

## What stage is the project at?
I consider Auto-Jimmy as being in open Beta. It's had as much testing as it can realistically be
given privately, so now it needs to be released to the world to get wider feedback. I'd only really
consider it out of beta when I've had confirmation from a wider audience that my implementation
of the various rules are accurate.
Issues can be raised on [GitHub](https://github.com/cthulhustig/autojimmy/issues). Log files can
be found in `%AppData%\Auto-Jimmy\`on Windows and `~/.auto-jimmy/` on Linux and macOS.

## Are you going to add Mongoose ship construction?
Maybe, it will most likely come down to a combination of user feedback and my motivation. The
Gunsmith implementation took a LONG time. A lot of that was having to create the framework and
UI elements that would allow this kind of complex construction, I suspect a lot of that could be
reused to simplify the creation of a ship construction tool. The other factor that contributed to
the Gunsmith taking so long to implement was ambiguities in the Field Catalogue rules. From my
limited experience of the ship creation rules, they're more complex than the weapon creation rules
but don't have the same level of ambiguities, this makes me think they _might_ not be so
complicated to implement. The main thing that puts me off is the fact there are already very good
spreadsheets that implement the ship creation process, so I'm not sure if another tool is actually
needed.

## Why isn't the code very pythonic?
My core skills are as a C++ developer, so you'll probably find that influences the code I write.
This project is orders of magnitude larger than all the other Python code I've written combined. I
was very much learning the intricacies of the language as I went, so you'll find that newer code is
more pythonic than older code.

## Why on earth did you use Python?
I don't think I would have gotten the project this far if I hadn't. Python allowed me to "hack
together" code incredibly quickly, which helped keep motivation high. However, there are some
aspects of Python that have been problematic as the size and complexity of the project has
increased, the main culprits being the lack of strong typing and lack of "real" threading.

## Why do you hand roll your Qt UI code rather than use something like Qt Designer?
This is for a couple of reasons:
1. This is the first time I've used Qt, so the ability to find help was going to be very important.
I did some investigation when I was choosing a UI framework and I found that most Qt help on places
like Stack Overflow was aimed at hand rolled code rather than using Qt Designer.
2. I'm old enough that the majority of my UI skills are from a time when UI creation tools were
terrible. It means I'm used to doing it this way and to be honest I kind of enjoy it.

## Why are you using Qt5 instead of Qt6?
My friend who runs our Traveller game uses a laptop running macOS Sierra. Qt6 isn't supported on
Sierra and I wanted him to be able to run the application.
