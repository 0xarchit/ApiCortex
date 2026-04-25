CREATE TABLE IF NOT EXISTS "notifications" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"org_id" uuid NOT NULL,
	"title" varchar(255) NOT NULL,
	"message" varchar(2048) NOT NULL,
	"severity" varchar(16) NOT NULL DEFAULT 'info',
	"source" varchar(64) NOT NULL DEFAULT 'system',
	"metadata" jsonb,
	"is_read" boolean NOT NULL DEFAULT false,
	"read_at" timestamp with time zone,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);--> statement-breakpoint
ALTER TABLE "notifications" ADD CONSTRAINT "notifications_org_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "public"."organizations"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "ix_notifications_org_id" ON "notifications" USING btree ("org_id");--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "ix_notifications_is_read" ON "notifications" USING btree ("is_read");--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "ix_notifications_created_at" ON "notifications" USING btree ("created_at");