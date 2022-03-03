let res = [
  db.accounts.insertOne({
    id: UUID(),
    email: "admin@example.com",
    is_active: true,
    is_superuser: true,
    is_verified: true,
    hashed_password:
      "$2b$12$LuqZ828H/CJY90kTANEaxuDNLSw4WEeJoSPlvJzSsOoI9x7uHVzQa",
    first_name: "Admin",
    last_name: "",
    clients: null,
    created_at: new Date("2022-03-03T13:42:59.831Z"),
    updated_at: new Date("2022-03-03T13:42:59.831Z"),
  }),
  db.chats.createIndex(
    {
      title: "text",
      username: "text",
      description: "text",
    },
    { default_language: "none" }
  ),
  db.chats.createIndex({
    type: 1,
    is_verified: 1,
    is_restricted: 1,
    is_creator: 1,
    is_scam: 1,
    is_fake: 1,
    is_support: 1,
    members_count: 1,
    updated_at: -1, // most recent
    scraped_at: -1, // most recent
  }),

  db.messages.createIndex(
    {
      text: "text",
      caption: "text",
    },
    { default_language: "none" }
  ),
  db.messages.createIndex({
    "from_user._id": 1,
    "chat._id": 1,
    date: -1, // most recent
    views: 1,
    is_empty: 1,
    "attachment.type": 1,
    "forward.from_chat._id": 1,
    "forward.from_user._id": 1,
  }),

  db.users.createIndex(
    {
      title: "text",
      username: "text",
      first_name: "text",
      last_name: "text",
    },
    { default_language: "none" }
  ),
  db.users.createIndex({
    is_deleted: 1,
    is_bot: 1,
    is_verified: 1,
    is_restricted: 1,
    is_scam: 1,
    is_fake: 1,
    is_support: 1,
    phone_number: 1,
    updated_at: -1, // most recent
  }),
  db.createCollection("metrics", {
    timeseries: {
      timeField: "ts",
      metaField: "metadata",
      granularity: "seconds",
    },
  }),
];

printjson(res);
