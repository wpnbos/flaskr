DROP TABLE comment; 

CREATE TABLE comment (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	parent_id INTEGER DEFAULT NULL,
	post_id INTEGER,  
	body text NOT NULL, 
	author_id INTEGER NOT NULL, 
	created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	likes INT NOT NULL DEFAULT 1,
	FOREIGN KEY (post_id) REFERENCES post (id), 
	FOREIGN KEY (parent_id) REFERENCES comments (id), 
	FOREIGN KEY (author_id) REFERENCES user (id)
);

INSERT INTO comment SELECT * FROM comments; 

DROP TABLE comments; 

ALTER TABLE comment RENAME TO comments;	