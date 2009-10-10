import java.io.IOException;
import javax.servlet.http.*;

public class JythonTutorialServlet extends HttpServlet {
    public void doPost(HttpServletRequest req, HttpServletResponse resp)
            throws IOException {
        resp.setContentType("application/json; charset=utf-8");
        resp.getWriter().println("'The jython version of python-tutorial.appspot.com is not yet working'");
    }
}
