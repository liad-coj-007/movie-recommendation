package main

import (
	"fmt"
	"movies_recommender/src/DB/DB_interface"
)

func main() {
	conn := db.ConnectDB()
	err := db.CreateTables(conn)
	if err != nil {
		fmt.Println("Error creating table:", err)
		return
	}

	fmt.Println("Table created successfully:")

	defer conn.Close()
}