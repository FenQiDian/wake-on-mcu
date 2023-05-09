use anyhow::Result;
use env_logger::{Builder, Target, WriteStyle};
use log::{info, error, LevelFilter};
use tokio::net::UdpSocket;
use std::env;
use std::fs::OpenOptions;
use std::net::{IpAddr, SocketAddr};
use std::string::String;

fn main() -> Result<()> {
    let mut builder = Builder::new();

    if env::consts::OS == "windows" {
        let mut path = std::env::current_exe()?;
        path.pop();
        path = path.join("womagent.log");
        let file = OpenOptions::new()
            .write(true)
            .append(true)
            .create(true)
            .open(path)?;
        builder.target(Target::Pipe(Box::new(file)));

    } else if env::consts::OS == "linux" {
        let file = OpenOptions::new()
            .write(true)
            .append(true)
            .create(true)
            .open("/var/log/womagent.log")?;
        builder.target(Target::Pipe(Box::new(file)));
    }

    builder
        .filter_level(LevelFilter::Info)
        .write_style(WriteStyle::Never)
        .init();

    match platform::run() {
        Ok(_) => {
            info!("exit ok");
            return Ok(())
        },
        Err(err) => {
            error!("exit err {}", err);
            return Err(err);
        }
    };
}

const IP_ADDR: [u8; 4] = [0, 0, 0, 0];
const PORT: u16 = 40004;
const MAGIC_SHUTDOWN: &str = "wom_shutdown";

async fn handle_udp() -> Result<()> {
    info!("enter udp");
    let ip_addr = IpAddr::from(IP_ADDR);
    let server_addr = SocketAddr::new(ip_addr, PORT);
    let socket = UdpSocket::bind(server_addr).await?;
    let mut buf = [0u8; 1500];

    info!("listen udp");
    loop {
        let (size, _) = socket.recv_from(&mut buf).await?;
        let content = String::from_utf8_lossy(&buf[..size]);
        if MAGIC_SHUTDOWN != content {
            info!("unknown packet {}", content);
            continue;
        } else {
            return Ok(());
        }
    }
}

#[cfg(target_os = "linux")]
mod platform {
    use anyhow::Result;
    use daemonize::Daemonize;
    use log::info;
    use tokio::runtime::Builder;
    use tokio::signal::unix::{signal, SignalKind};
    use std::process::Command;

    pub fn run() -> Result<()> {
        let _daemonize = Daemonize::new()
            .pid_file("/var/run/womagent.pid") // Every method except `new` and `start`
            .chown_pid_file(true) // is optional, see `Daemonize` documentation
            .working_directory("/tmp") // for default behaviour.
            .user("root")
            .start()?;

        info!("started ok");

        let rt = Builder::new_current_thread().enable_io().build()?;
        return rt.block_on(async {
            let mut sig = signal(SignalKind::terminate())?;
            loop {
                tokio::select! {
                    opt = sig.recv() => {
                        if opt.is_some() {
                            info!("receive signal");
                        } else {
                            info!("receive unknown");
                        }
                        return Ok(());
                    },
                    res = crate::handle_udp() => {
                        res?;
                        info!("shutdown request");
                        Command::new("shutdown")
                            .arg("-h")
                            .arg("now")
                            .spawn()?;
                    },
                }
            }
        });
    }
}

#[cfg(windows)]
mod platform {
    use anyhow::Result;
    use log::{info, error};
    use tokio::runtime::Builder;
    use tokio::sync::mpsc;
    use std::ffi::OsString;
    use std::process::Command;
    use std::time::Duration;
    use windows_service::define_windows_service;
    use windows_service::service::{
        ServiceControl, ServiceControlAccept, ServiceExitCode, ServiceState, ServiceStatus,
        ServiceType,
    };
    use windows_service::service_control_handler::{self, ServiceControlHandlerResult};
    use windows_service::{service_dispatcher};

    const SERVICE_NAME: &str = "womagent";
    const SERVICE_TYPE: ServiceType = ServiceType::OWN_PROCESS;

    pub fn run() -> Result<()> {
        info!("started ok");
        service_dispatcher::start(SERVICE_NAME, ffi_service_main)?;
        return Ok(());
    }

    define_windows_service!(ffi_service_main, service_main);

    pub fn service_main(_arguments: Vec<OsString>) {
        if let Err(err) = run_service() {
            error!("service main err {}", err);
        }
    }

    pub fn run_service() -> Result<()> {
        let (exit_tx, mut exit_rx) = mpsc::channel(8);

        let event_handler = move |control_event| -> ServiceControlHandlerResult {
            match control_event {
                ServiceControl::Interrogate => ServiceControlHandlerResult::NoError,
                ServiceControl::Stop => {
                    exit_tx.blocking_send(()).unwrap();
                    ServiceControlHandlerResult::NoError
                }
                _ => ServiceControlHandlerResult::NotImplemented,
            }
        };

        let status_handle = service_control_handler::register(SERVICE_NAME, event_handler)?;
        status_handle.set_service_status(ServiceStatus {
            service_type: SERVICE_TYPE,
            current_state: ServiceState::Running,
            controls_accepted: ServiceControlAccept::STOP,
            exit_code: ServiceExitCode::Win32(0),
            checkpoint: 0,
            wait_hint: Duration::default(),
            process_id: None,
        })?;

        let rt = Builder::new_current_thread().enable_io().build()?;
        let res = rt.block_on(async {
            loop {
                tokio::select! {
                    opt = exit_rx.recv() => {
                        if opt.is_some() {
                            info!("receive signal");
                        } else {
                            info!("receive unknown");
                        }
                        return Ok(());
                    },
                    res = crate::handle_udp() => {
                        res?;
                        info!("shutdown request");
                        Command::new("shutdown")
                            .arg("/s")
                            .arg("/t")
                            .arg("5")
                            .spawn()
                            .expect("shutdown failed");
                    },
                }
            }
        });

        // Tell the system that service has stopped.
        status_handle.set_service_status(ServiceStatus {
            service_type: SERVICE_TYPE,
            current_state: ServiceState::Stopped,
            controls_accepted: ServiceControlAccept::empty(),
            exit_code: ServiceExitCode::Win32(0),
            checkpoint: 0,
            wait_hint: Duration::default(),
            process_id: None,
        })?;

        return res;
    }
}
