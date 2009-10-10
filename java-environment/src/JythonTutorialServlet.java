import java.io.IOException;
import javax.servlet.http.*;
import org.python.util.PythonInterpreter;

public class JythonTutorialServlet extends HttpServlet {
    public void doPost(HttpServletRequest req, HttpServletResponse resp)
	throws IOException {
	PythonInterpreter interp = new PythonInterpreter();
	String tutorial_dir = this.getServletContext()
	    .getRealPath("/WEB-INF/python-tutorial");
	String jython_dir = this.getServletContext()
	    .getRealPath("/WEB-INF/JythonLib");
	interp.set("tutorial_dir", tutorial_dir);
	interp.set("jython_dir", jython_dir);
	interp.exec("import sys");
	interp.exec("sys.path.insert(0, jython_dir)");
	interp.exec("sys.path.insert(0, tutorial_dir)");
	interp.set("req_data", Funcs.read_all_bytes(req.getInputStream()));
	interp.exec("import simplejson");
	interp.exec("string = ''.join(chr(x) for x in req_data)");
	interp.exec("json = simplejson.loads(string)");
        interp.exec("assert not json[u'method'].startswith(u'_'), "
		    + "json[u'method']");
	interp.exec("import tutorial");
	interp.exec("handler = tutorial.TutorialWebService()");
        interp.exec("method = getattr(handler, "
		    + "json[u'method'].encode('ascii'))");
        interp.exec("result = method(*json[u'params'])");
	interp.exec("resp_data = result.encode('utf-8')");
	interp.set("resp", resp);
	interp.exec("resp.setContentType('application/json; charset=utf-8')");
	interp.exec("resp_json = simplejson.dumps(resp_data).encode('utf-8')");
	interp.exec("resp.getOutputStream().write(resp_json)");
    }
}
