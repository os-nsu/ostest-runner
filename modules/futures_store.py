class FuturesStore:
    def __init__(self, max_futures):
        self.__futures_to_worker_num = {}
        self.__max_futures = max_futures

    def get_next_worker_num(self):
        for i in range(self.__max_futures):
            if i not in self.__futures_to_worker_num.values():
                return i
        raise Exception("Could not find next worker index")

    def append(self, future):
        if future in self.__futures_to_worker_num:
            raise Exception("Future was already added")
        if len(self.__futures_to_worker_num) >= self.__max_futures:
            raise Exception("Tried to add future, but there are no worker slots left")
        worker_num = self.get_next_worker_num()
        self.__futures_to_worker_num[future] = worker_num

    def remove(self, future):
        if future not in self.__futures_to_worker_num:
            raise Exception("Future to be removed was not found in the list of futures")
        self.__futures_to_worker_num.pop(future)

    def __len__(self):
        return len(self.__futures_to_worker_num)

    def __iter__(self):
        """this method returns a copied list"""
        return list(self.__futures_to_worker_num.keys()).__iter__()
