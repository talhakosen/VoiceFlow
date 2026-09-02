import Dependencies
import Foundation

/// Python backend SÜRECİNİ yöneten dependency.
///
/// `BackendClient` HTTP konuşur; backend ölüyse onun çağrıları hiçbir şeyi kurtaramaz.
/// "Servisi Yeniden Başlat" / "Zorla Yeniden Başlat" bu client'a gitmeli — daha önce
/// sadece `POST /api/force-stop` atıyorlardı, yani ölü servise istek gönderip
/// sessizce başarısız oluyorlardı (kullanıcı açısından: buton hiçbir şey yapmıyor).
struct BackendProcessClient {
    /// SIGTERM → gerekirse SIGKILL → yeniden başlat → /health bekle.
    var restart: () async -> Bool
    /// Port üzerindeki her şeyi SIGKILL → yeniden başlat → /health bekle.
    var hardReset: () async -> Bool
    /// /health 200 dönüyor mu?
    var isHealthy: () async -> Bool
    /// Son başarısızlık nedeni (kullanıcıya gösterilebilir), yoksa nil.
    var lastFailureMessage: () -> String?
}

extension BackendProcessClient: DependencyKey {
    static let liveValue = BackendProcessClient(
        restart: {
            await withCheckedContinuation { cont in
                DispatchQueue.main.async {
                    BackendProcessManager.shared.restart { cont.resume(returning: $0) }
                }
            }
        },
        hardReset: {
            await withCheckedContinuation { cont in
                DispatchQueue.main.async {
                    BackendProcessManager.shared.hardReset { cont.resume(returning: $0) }
                }
            }
        },
        isHealthy: {
            await withCheckedContinuation { cont in
                BackendProcessManager.shared.isHealthy { cont.resume(returning: $0) }
            }
        },
        lastFailureMessage: {
            BackendProcessManager.shared.lastFailure?.message
        }
    )

    static let testValue = BackendProcessClient(
        restart: { true },
        hardReset: { true },
        isHealthy: { true },
        lastFailureMessage: { nil }
    )
}

extension DependencyValues {
    var backendProcessClient: BackendProcessClient {
        get { self[BackendProcessClient.self] }
        set { self[BackendProcessClient.self] = newValue }
    }
}
