class EnftyContract:

    singleton = None

    def __init__(self):
        if EnftyContract.singleton == None:
            EnftyContract.singleton = EnftyContract()
        pass

    def mint(self):
        pass