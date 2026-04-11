use std::sync::Arc;

use axum::{
    extract::State,
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use tower_http::{cors::CorsLayer, trace::TraceLayer};
use tracing::info;
use tracing_subscriber::{fmt, EnvFilter};

mod executor;
mod models;

use executor::Executor;
use models::{ExecuteRequest, ExecuteResponse};

#[derive(Clone)]
struct AppState {
    executor: Arc<Executor>,
}

async fn health() -> impl IntoResponse {
    Json(serde_json::json!({ "status": "ok" }))
}

async fn execute_handler(
    State(state): State<AppState>,
    Json(payload): Json<ExecuteRequest>,
) -> impl IntoResponse {
    let test_id = payload.test_id.clone();
    match state.executor.execute(payload).await {
        Ok(result) => {
            let resp = ExecuteResponse::ok(test_id, result);
            (StatusCode::OK, Json(resp)).into_response()
        }
        Err(e) => {
            let resp = ExecuteResponse::err(test_id, e.to_string());
            (StatusCode::OK, Json(resp)).into_response()
        }
    }
}

#[tokio::main]
async fn main() {
    fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")),
        )
        .json()
        .init();

    let state = AppState {
        executor: Arc::new(Executor::new()),
    };

    let app = Router::new()
        .route("/health", get(health))
        .route("/v1/execute", post(execute_handler))
        .layer(CorsLayer::permissive())
        .layer(TraceLayer::new_for_http())
        .with_state(state);

    let addr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "0.0.0.0:9090".to_string());
    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .expect("failed to bind");

    info!(addr = %addr, "api-testing executor started");

    axum::serve(listener, app).await.expect("server error");
}
