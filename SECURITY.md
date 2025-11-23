# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

We take the security of FIML seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### Please Do NOT:

- Open a public GitHub issue for security vulnerabilities
- Disclose the vulnerability publicly before it has been addressed

### Please Do:

1. **Email us privately** at security@fiml.dev (or create a private security advisory on GitHub)
2. **Include the following information:**
   - Description of the vulnerability
   - Steps to reproduce the issue
   - Potential impact
   - Suggested fix (if any)
   - Your contact information for follow-up

### What to Expect:

- **Acknowledgment**: We will acknowledge receipt of your vulnerability report within 48 hours
- **Updates**: We will keep you informed about our progress addressing the issue
- **Timeline**: We aim to address critical vulnerabilities within 7 days
- **Credit**: With your permission, we will credit you in our security advisories

## Security Best Practices

When using FIML, please follow these security best practices:

### API Keys and Secrets

- **Never commit API keys or secrets** to version control
- Use environment variables or secure secret management systems
- Rotate API keys regularly
- Use separate keys for development and production

### Configuration

- Review and customize `.env.example` for your environment
- Use strong, unique passwords for database connections
- Enable TLS/SSL for production deployments
- Implement proper authentication and authorization

### Network Security

- Use HTTPS for all API communications
- Implement rate limiting to prevent abuse
- Configure firewalls to restrict access to services
- Use VPCs or private networks for internal services

### Database Security

- Use strong passwords for database users
- Limit database user permissions to minimum required
- Enable database encryption at rest and in transit
- Regularly backup and test restoration procedures

### Monitoring and Logging

- Enable audit logging for sensitive operations
- Monitor for suspicious activity
- Set up alerts for security-relevant events
- Regularly review logs for anomalies

### Dependencies

- Keep all dependencies up to date
- Regularly review security advisories
- Use tools like `pip-audit` or Dependabot
- Review and test updates before deploying

## Known Security Considerations

### Data Privacy

- FIML processes financial data; ensure compliance with relevant regulations
- Implement proper data retention and deletion policies
- Use encryption for sensitive data at rest and in transit

### Authentication

- The current version uses API key authentication
- Consider implementing OAuth 2.0 or JWT for production use
- Implement proper session management and timeout policies

### Rate Limiting

- Implement rate limiting to prevent abuse
- Monitor for unusual usage patterns
- Set appropriate quotas per user/API key

## Security Features

FIML includes the following security features:

- **Environment-based configuration**: Secrets loaded from environment variables
- **Input validation**: Pydantic models for request validation
- **SQL injection protection**: Parameterized queries via SQLAlchemy
- **CORS configuration**: Customizable CORS policies
- **Health checks**: Monitoring endpoints for service health

## Compliance

FIML provides tools to help with compliance:

- **Regional compliance checks**: Support for US, EU, UK, JP regulations
- **Audit logging**: Track all data access and modifications
- **Disclaimers**: Automatic generation of financial disclaimers
- **Data retention**: Configurable cache and data retention policies

## Security Updates

Security updates will be released as patch versions and announced via:

- GitHub Security Advisories
- Release notes
- Email notifications (for registered users)

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)

## Contact

For security-related questions or concerns:

- Security issues: security@fiml.dev
- General questions: support@fiml.dev
- GitHub: [Create a private security advisory](https://github.com/kiarashplusplus/FIML/security/advisories/new)

Thank you for helping keep FIML and our users safe!
