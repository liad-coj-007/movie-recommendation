package main

import (
	"fmt"
	"movies_recommender/src/DB/DB_interface"
)

func main() {
	conn := db.ConnectDB()
	db.CreateIdxs(conn)
	fmt.Println("finished!")

}