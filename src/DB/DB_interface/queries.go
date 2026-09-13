package db

import (
	"context"
	"github.com/jackc/pgx/v5/pgxpool"
)

func BuildUsersEmbedings(conn *pgxpool.Pool, userIdList []int64) (map[int64][]float32,Status) {
	query := `
		SELECT U.user_id, ARRAY_AGG(COALESCE(UR.avg_rating, 0.0) ORDER BY G.genre_id) AS embeddings
		FROM users U CROSS JOIN genres AS G LEFT JOIN user_genre_ratings AS UR ON G.genre_id = UR.genre_id AND
		U.user_id = UR.user_id
		WHERE U.user_id = ANY($1::BIGINT[])
		GROUP BY U.user_id 
	`

	rows ,err := conn.Query(context.Background(),query,userIdList)
	if err != nil {
		return nil,mapErrorToStatus(err)
	}

	defer rows.Close()

	results := make(map[int64][]float32 , len(userIdList))
	for rows.Next(){
		var userId int64 
		var embeddings []float32
		if err := rows.Scan(&userId,&embeddings); err != nil {
			return nil,mapErrorToStatus(err)
		}
		results[userId] = embeddings
	}

	return results,Success

}
