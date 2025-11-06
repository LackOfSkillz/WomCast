import React from 'react';
import type { LegalTermsResponse } from '../../services/api';
import './LegalNoticeDialog.css';

interface LegalNoticeDialogProps {
  open: boolean;
  terms: LegalTermsResponse | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  onAccept: () => void;
  acknowledging: boolean;
}

export const LegalNoticeDialog: React.FC<LegalNoticeDialogProps> = ({
  open,
  terms,
  loading,
  error,
  onRetry,
  onAccept,
  acknowledging,
}) => {
  if (!open) {
    return null;
  }

  const acceptedVersion = terms?.accepted?.version;
  const acceptedAt = terms?.accepted?.accepted_at;
  const acceptedDisplay = (() => {
    if (!acceptedAt) {
      return null;
    }
    const parsed = new Date(acceptedAt);
    if (Number.isNaN(parsed.getTime())) {
      return acceptedAt;
    }
    try {
      return new Intl.DateTimeFormat(undefined, {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(parsed);
    } catch (error) {
      console.warn('Failed to format acceptance timestamp', error);
      return parsed.toISOString();
    }
  })();

  return (
    <div className="legal-dialog__backdrop" role="presentation">
      <div
        className="legal-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="legal-dialog-title"
      >
        <header className="legal-dialog__header">
          <div>
            <h1 id="legal-dialog-title">{terms?.title ?? 'Legal Notice'}</h1>
            {terms ? (
              <p className="legal-dialog__subtitle">
                Last updated {terms.last_updated}. Version {terms.version}.
              </p>
            ) : null}
          </div>
        </header>

        <div className="legal-dialog__body">
          {loading ? (
            <div className="legal-dialog__state">Loading legal terms…</div>
          ) : null}

          {!loading && error ? (
            <div className="legal-dialog__error" role="alert">
              <p>{error}</p>
              <button type="button" onClick={onRetry} className="legal-dialog__retry">
                Retry
              </button>
            </div>
          ) : null}

          {!loading && !error && terms ? (
            <div className="legal-dialog__content">
              <p className="legal-dialog__intro">{terms.intro}</p>

              {acceptedVersion ? (
                <div className="legal-dialog__accepted">
                  <strong>Current acknowledgement:</strong> Version {acceptedVersion}
                  {acceptedDisplay ? ` • accepted ${acceptedDisplay}` : ''}
                </div>
              ) : null}

              <div className="legal-dialog__sections">
                {terms.sections.map((section) => (
                  <section key={section.title}>
                    <h2>{section.title}</h2>
                    <ul>
                      {section.items.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </section>
                ))}
              </div>

              <section className="legal-dialog__providers">
                <h2>Provider Terms</h2>
                <ul>
                  {terms.providers.map((provider) => (
                    <li key={provider.name}>
                      <span className="legal-dialog__provider-name">{provider.name}</span>
                      <div className="legal-dialog__provider-links">
                        <a href={provider.terms_url} target="_blank" rel="noreferrer">
                          Terms
                        </a>
                        {provider.privacy_url ? (
                          <a href={provider.privacy_url} target="_blank" rel="noreferrer">
                            Privacy
                          </a>
                        ) : null}
                      </div>
                      {provider.notes ? (
                        <p className="legal-dialog__provider-notes">{provider.notes}</p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </section>
            </div>
          ) : null}
        </div>

        <footer className="legal-dialog__footer">
          <button
            type="button"
            className="legal-dialog__primary"
            onClick={onAccept}
            disabled={loading || acknowledging || Boolean(error) || !terms}
          >
            {acknowledging ? 'Saving…' : 'I Agree'}
          </button>
        </footer>
      </div>
    </div>
  );
};
