CREATE TABLE IF NOT EXISTS links (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  slug          TEXT    NOT NULL,
  target_url    TEXT    NOT NULL CHECK (length(target_url) <= 2048)
                         CHECK (
                           substr(lower(target_url),1,7) = 'http://' OR
                           substr(lower(target_url),1,8) = 'https://'
                         ),
  is_permanent  INTEGER NOT NULL DEFAULT 1 CHECK (is_permanent IN (0,1)),
  created_at    DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  created_ip    TEXT,
  note          TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_links_slug ON links(slug);

CREATE INDEX IF NOT EXISTS idx_links_created_at ON links(created_at);

CREATE TABLE IF NOT EXISTS clicks (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  link_id    INTEGER NOT NULL,
  ts         DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  ip         TEXT,
  user_agent TEXT,
  referrer   TEXT,
  FOREIGN KEY (link_id) REFERENCES links(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_clicks_link_id ON clicks(link_id);
CREATE INDEX IF NOT EXISTS idx_clicks_ts      ON clicks(ts);