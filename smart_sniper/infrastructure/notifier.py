from smart_sniper.application.ports import NotifierPort


class SystemNotifier(NotifierPort):
    def __init__(self, root=None) -> None:
        self.root = root

    def notify_slot_found(self) -> None:
        try:
            if self.root is not None:
                self.root.bell()
            else:
                print("\a", end="", flush=True)
        except Exception:
            pass

