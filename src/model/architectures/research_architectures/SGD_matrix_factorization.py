from surprise import Dataset, Reader, SVD
from sklearn.base import BaseEstimator, RegressorMixin
import numpy as np

class SGDMatrixFacorization(BaseEstimator, RegressorMixin):
    def __init__(self,rating_scale,n_epochs=50,n_factors=50,lr_all=0.005,reg_all=0.02):
        self.model = SVD(
            n_factors=n_factors,
            lr_all=lr_all,
            reg_all=reg_all,
            n_epochs=n_epochs
        )
        self.rating_scale = rating_scale
        self.n_factors = n_factors
        self.lr_all = lr_all
        self.reg_all = reg_all
        self.n_epochs=n_epochs

    def fit(self,X,y):
        train =  X.copy()
        train["rating"] = y.values
        reader = Reader(
            rating_scale=self.rating_scale
        )

        train = Dataset.load_from_df(
            train,reader
        ).build_full_trainset()

        self.model.fit(train)
        return self

    
    def predict(self, X):

        user_idx = np.array([
            self.model.trainset.to_inner_uid(uid)
            for uid in X["userId"]
        ])

        movie_idx = np.array([
            self.model.trainset.to_inner_iid(iid)
            for iid in X["movieId"]
        ])

        pred = (
            self.model.trainset.global_mean
            + self.model.bu[user_idx]
            + self.model.bi[movie_idx]
            + np.sum(
                self.model.pu[user_idx] *
                self.model.qi[movie_idx],
                axis=1
            )
        )

        return np.clip(pred, self.rating_scale[0], self.rating_scale[1])
