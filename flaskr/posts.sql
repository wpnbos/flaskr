DROP TABLE posts; 

CREATE TABLE posts (
	id INTEGER PRIMARY KEY AUTOINCREMENT, 
	author_id INTEGER NOT NULL, 
	created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	title TEXT NOT NULL, 
	body TEXT, 
	likes INT NOT NULL DEFAULT 1, 
	image TEXT DEFAULT NULL,
	FOREIGN KEY (author_id) REFERENCES user (id)
);

INSERT INTO posts (id, author_id, created, title, body, likes) SELECT * FROM post; 

DROP TABLE post; 

ALTER TABLE posts RENAME TO post;	