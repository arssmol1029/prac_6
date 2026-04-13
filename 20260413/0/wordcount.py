import locale
import gettext
import random


def init_locale():
    global _, ngettext, ngettexte

    locale.setlocale(locale.LC_ALL, locale.getlocale())
    translation = gettext.translation("wordcount", "po", fallback=True)
    _ = translation.gettext
    ngettext = translation.ngettext
    
    translatione = gettext.translation("wordcounte", "po", fallback=True)
    ngettexte = translatione.ngettext


def main():
    init_locale()

    try:
        while line := input():
            n = len(line.split())
            if random.random() < 0.5:
                print(ngettext("Entered {} word", "Entered {} words", n).format(len(line.split())))
            else:
                print(ngettexte("Entered {} word", "Entered {} words", n).format(len(line.split())))
    except Exception as e:
        print(e)
    except KeyboardInterrupt:
        pass
    finally:
        print(_("Done!"))


if __name__ == "__main__":
    main()