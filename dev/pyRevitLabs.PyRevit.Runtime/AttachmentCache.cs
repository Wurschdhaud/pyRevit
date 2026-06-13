using System;

using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Session-scoped cache for the active pyRevit attachment.
    /// <para>
    /// PyRevitAttachments.GetAttached() re-reads the addin manifests and the
    /// clones registry from disk on every call, but the attachment Revit
    /// launched with can not change for the running session. The result is
    /// stored in AppDomain data so all script engines (startup scripts,
    /// smartbuttons, commands, hooks) share a single disk lookup.
    /// </para>
    /// <para>
    /// The cache is intentionally NOT inside pyRevitLabs.PyRevit since that
    /// assembly is shared with the CLI, where attachments are mutated and
    /// re-read within a single invocation. It is cleared on session reload
    /// by sessionmgr.load_session().
    /// </para>
    /// </summary>
    public static class AttachmentCache {
        public static PyRevitAttachment GetAttached(int revitYear) {
            var cached =
                AppDomain.CurrentDomain.GetData(DomainStorageKeys.AttachmentCacheKey) as PyRevitAttachment;
            if (cached != null && cached.Product != null && cached.Product.ProductYear == revitYear)
                return cached;

            var attachment = PyRevitAttachments.GetAttached(revitYear);
            if (attachment != null)
                AppDomain.CurrentDomain.SetData(DomainStorageKeys.AttachmentCacheKey, attachment);
            return attachment;
        }

        public static void Clear() {
            AppDomain.CurrentDomain.SetData(DomainStorageKeys.AttachmentCacheKey, null);
        }
    }
}
