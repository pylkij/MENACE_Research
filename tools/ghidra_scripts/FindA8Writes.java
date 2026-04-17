import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;

public class FindA8Writes extends GhidraScript {

    @Override
    public void run() throws Exception {
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);

        FunctionIterator funcs = currentProgram.getFunctionManager().getFunctions(true);
        int count = 0;

        while (funcs.hasNext()) {
            if (monitor.isCancelled()) break;
            Function func = funcs.next();

            DecompileResults res = decompiler.decompileFunction(func, 10, monitor);
            if (res == null) continue;

            ghidra.app.decompiler.DecompiledFunction decomp = res.getDecompiledFunction();
            if (decomp == null) continue;

            String code = decomp.getC();
            if (code != null && code.contains("0xa8) =")) {
                println(func.getName() + " @ " + func.getEntryPoint());
                count++;
            }
        }

        println("Done. Found " + count + " functions.");
    }
}