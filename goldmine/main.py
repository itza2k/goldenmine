from goldmine.ui.app import GoldmineApp
from goldmine.ui.theme import apply_theme


def main() -> None:
    apply_theme("light")
    app = GoldmineApp()
    app.mainloop()


if __name__ == "__main__":
    main()
