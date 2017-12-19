from modelgym.models.learning_task import LearningTask
from collections import defaultdict

from sklearn import preprocessing, pipeline

import numpy as np

class CatCounter:
    def __init__(self, learning_task, sort_values=None, seed=0):
        self.learning_task = learning_task
        self.sort_values = sort_values
        self.seed = seed
        self.sum_dicts = defaultdict(lambda: defaultdict(float))
        self.count_dicts = defaultdict(lambda: defaultdict(float))

    def update(self, value, col, key):
        self.sum_dicts[col][key] += value
        self.count_dicts[col][key] += 1

    def counter(self, key, col):
        num, den = self.sum_dicts[col][key], self.count_dicts[col][key]
        if self.learning_task == LearningTask.CLASSIFICATION:
            return (num + 1.) / (den + 2.)
        elif self.learning_task == LearningTask.REGRESSION:
            return num / den if den > 0 else 0
        else:
            raise ValueError('Task type must be classification or regression')

    def fit(self, X, y):
        self.sum_dicts = defaultdict(lambda: defaultdict(float))
        self.count_dicts = defaultdict(lambda: defaultdict(float))

        if self.sort_values is None:
            indices = np.arange(X.shape[0])
            np.random.seed(self.seed)
            np.random.shuffle(indices)
        else:
            indices = np.argsort(self.sort_values)

        results = [np.zeros((X.shape[0], 0))]
        for col in range(X.shape[1]):
            result = np.zeros(X.shape[0])
            for index in indices:
                key = X[index, col]
                result[index] = self.counter(key, col)
                self.update(y[index], col, key)
            results.append(result.reshape(-1, 1))

        return np.concatenate(results, axis=1)

    def transform(self, X):
        results = [np.zeros((X.shape[0], 0))]
        for col in range(X.shape[1]):
            result = np.zeros(X.shape[0])
            for index in range(X.shape[0]):
                key = X[index, col]
                result[index] = self.counter(key, col)
            results.append(result.reshape(-1, 1))
        return np.concatenate(results, axis=1)


class OneHotEncoder:
    def __init__(self):
        self.enc = dict()

    def fit(self, X):
        return self.__apply(X, self.__fit)

    def transform(self, X):
        return self.__apply(X, self.__transform)

    def __apply(self, X, func):
        X_encoded = []
        for i in np.arange(X.shape[1]):
            cur_one_hot_cols = func(np.array(X[:, i], dtype=int), i)
            X_encoded.append(cur_one_hot_cols)

        return np.concatenate(X_encoded, axis=1)

    def __fit(self, data, index):
        self.enc[index] = preprocessing.LabelBinarizer()
        return self.enc[index].fit_transform(data)

    def __transform(self, data, index):
        try:
            return self.enc[index].transform(data)
        except:
            raise ValueError("Test set contains labels which" +
                        "are not represented in train set.\n" +
                        "You may decrease one_hot_max_size to avoid this error."
                            )


def preprocess_cat_cols(X_train, y_train, cat_cols=[], X_test=None,
                        one_hot_max_size=1, learning_task=LearningTask.CLASSIFICATION):
    """
        one-hot or cat-count preprocessing, depends on one_hot_max_size
        :return X_train [, X_test] - transformed data
    """
    one_hot_cols = [col for col in cat_cols
        if len(np.unique(X_train[:, col])) <= one_hot_max_size]

    cat_count_cols = list(set(cat_cols) - set(one_hot_cols))

    preprocess_counter_cols(X_train, y_train, cat_count_cols,
            X_test, learning_task=learning_task)

    X_train, X_test =  preprocess_one_hot_cols(X_train, one_hot_cols, X_test)

    if X_test is None:
        return X_train
    else:
        return X_train, X_test



def preprocess_counter_cols(X_train, y_train, cat_cols=None, X_test=None, cc=None,
                        counters_sort_col=None,
                        learning_task=LearningTask.CLASSIFICATION):
    if cat_cols is None or len(cat_cols) == 0:
        return cc
    if cc is None:
       sort_values = None if counters_sort_col is None else X_train[:, counters_sort_col]
       cc = CatCounter(learning_task, sort_values)
       X_train[:,cat_cols] = cc.fit(X_train[:,cat_cols], y_train)
    else:
       X_train[:,cat_cols] = cc.transform(X_train[:,cat_cols])
    if not X_test is None:
       X_test[:,cat_cols] = cc.transform(X_test[:,cat_cols])
    return cc


def preprocess_one_hot_cols(X_train, cat_cols=None, X_test=None):
    add_one_hot = lambda X_old, X_one_hot: np.concatenate(
                            (np.delete(X_old, cat_cols, 1), X_one_hot), 1)

    if cat_cols is None or len(cat_cols) == 0:
        return X_train, X_test

    enc = OneHotEncoder()
    X_train = add_one_hot(X_train, enc.fit(X_train[:, cat_cols]))

    if X_test is not None:
        X_test =  add_one_hot(X_test, enc.transform(X_test[:, cat_cols]))

    return X_train, X_test