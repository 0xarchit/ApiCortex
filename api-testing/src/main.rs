//! Entrypoint for the api-testing executor service.

use std::sync::Arc;
use tracing::info;
use tracing_subscriber::{fmt, EnvFilter};

use api_testing::{create_app, AppState};
use api_testing::executor::Executor;

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

    let app = create_app(state);

    let addr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "0.0.0.0:9090".to_string());
    
    // Create socket with SO_REUSEADDR to allow quick restarts on Windows
    let socket = create_reuseaddr_socket(&addr)
        .expect("failed to create socket");
    
    let listener = tokio::net::TcpListener::from_std(socket.into())
        .expect("failed to create listener");

    info!(addr = %addr, "api-testing executor started");

    axum::serve(listener, app).await.expect("server error");
}

fn create_reuseaddr_socket(addr: &str) -> Result<std::net::TcpListener, Box<dyn std::error::Error>> {
    use socket2::{Domain, Protocol, Socket, Type};
    
    let addr: std::net::SocketAddr = addr.parse()?;
    let socket = Socket::new(Domain::for_address(addr), Type::STREAM, Some(Protocol::TCP))?;
    
    // Enable SO_REUSEADDR - critical for quick restarts on Windows
    // This allows binding to a port in TIME_WAIT state
    socket.set_reuse_address(true)?;
    
    socket.bind(&addr.into())?;
    socket.listen(1024)?;
    
    Ok(socket.into())
}
