from sklearn.decomposition import NMF
from scipy.sparse import csr_matrix
import numpy as np


class SparseNMF(NMF):

    def __init__(
        self,
        num_of_movies,
        n_components=20,
        init=None,
        solver="cd",
        beta_loss="frobenius",
        tol=1e-4,
        max_iter=200,
        random_state=None
    ):
        self.num_of_movies = num_of_movies
        super().__init__(
            n_components=n_components,
            init=init,
            solver=solver,
            beta_loss=beta_loss,
            tol=tol,
            max_iter=max_iter,
            random_state=random_state
        )

    def fit(self, X, y):

        data = X.copy()
        data["rating"] = y.values

        self.user_ids_, user_idx = np.unique(
            data["userId"].values,
            return_inverse=True
        )

        self.movie_ids_, movie_idx = np.unique(
            data["movieId"].values,
            return_inverse=True
        )

        self.X_ = csr_matrix(
            (
                data["rating"].values,
                (user_idx, movie_idx)
            ),
            shape=(
                len(self.user_ids_),
                self.num_of_movies
            )
        )

        super().fit(self.X_)
        self.W_ = super().fit_transform(self.X_)
        return self

    def predict(self, X):

        user_idx = np.searchsorted(
            self.user_ids_,
            X["userId"].values
        )

        movie_idx = np.searchsorted(
            self.movie_ids_,
            X["movieId"].values
        )

        user_factors = self.W_[user_idx]

        movie_factors = self.components_.T[movie_idx]

        predictions = np.sum(
            user_factors * movie_factors,
            axis=1
        )

        predictions = np.clip(predictions, 0.5, 5)

        return predictions