init_sql = '''
CREATE TABLE t_article(
    aid BIGINT PRIMARY KEY,
    title VARCHAR NOT NULL,
    tags VARCHAR,
    categories VARCHAR,
    create_time DATETIME,
    update_time DATETIME
);
CREATE INDEX idx_t_article_title ON t_article(title);
CREATE INDEX idx_t_article_tags ON t_article(tags);
CREATE INDEX idx_t_article_categories ON t_article(categories);
CREATE INDEX idx_t_article_create_time ON t_article(create_time);
CREATE INDEX idx_t_article_update_time ON t_article(update_time);
'''